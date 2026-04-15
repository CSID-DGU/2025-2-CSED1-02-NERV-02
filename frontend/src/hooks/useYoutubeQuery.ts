import { useEffect } from 'react';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { fetchAnalysis, fetchTextAnalysis } from '../api/services';
import { useSettings, useDictionary } from './useSystemConfig';
import { derivePolicy } from '../features/analysis/policy';
import type {
  AnalyzedComment,
  AppSettings,
  FullAnalysisResponse,
  KeywordMode,
  YoutubeAnalysisResponse,
} from '../api/types';

const ANALYSIS_STORAGE_KEY = 'guard-filter-analysis';
const FILTER_RESULT_KEY = 'guard-filter-results';

const CACHE_TTL = 5 * 60 * 1000; // 5분

// ── 텍스트 정규화 (API textOriginal ↔ DOM textContent 차이 대응) ──
// content-script 의 ultraNormalize 와 정확히 동일한 규칙을 사용해야 한다.
// NFKC + 소문자 + 공백/zero-width/변이선택자/구두점/기호(이모지 포함) 제거.
function ultraNormalize(text: string): string {
  return text
    .normalize('NFKC')
    .toLowerCase()
    .replace(/[\s\u200B-\u200D\uFEFF\u00A0\uFE00-\uFE0F]/g, '')
    .replace(/[\p{P}\p{S}]/gu, '');
}

// ── 팝업 분석 캐시 (chrome.storage.session — 팝업 전용) ──

const saveAnalysisToStorage = async (videoId: string, signature: string, data: FullAnalysisResponse) => {
  if (typeof chrome !== 'undefined' && chrome.storage?.session) {
    await chrome.storage.session.set({ [ANALYSIS_STORAGE_KEY]: { videoId, signature, data, cachedAt: Date.now() } });
  }
};

const loadAnalysisFromStorage = async (videoId: string, signature: string): Promise<FullAnalysisResponse | null> => {
  if (typeof chrome !== 'undefined' && chrome.storage?.session) {
    const result = await chrome.storage.session.get(ANALYSIS_STORAGE_KEY);
    const cached = result[ANALYSIS_STORAGE_KEY] as { videoId: string; signature?: string; data: FullAnalysisResponse; cachedAt?: number } | undefined;
    if (
      cached &&
      cached.videoId === videoId &&
      cached.signature === signature &&
      cached.cachedAt &&
      Date.now() - cached.cachedAt < CACHE_TTL
    ) {
      return cached.data;
    }
  }
  return null;
};

// ── 필터링 결과를 chrome.storage.local에 저장 (content-script 접근 가능) ──
// 보안 모드는 서버 재호출 없이 클라이언트에서 derivePolicy로 재적용한다.
// content-script 는 comment_id 매칭을 1차, ultra-normalized text 매칭을 2차로 사용한다.
// 각 엔트리에 action/maskedText 를 함께 전달해 FULL_BLOCK vs PARTIAL_MASK 를
// content-script 가 구분 렌더링할 수 있게 한다.
interface FilterEntry {
  id: string;
  textNorm: string;
  action: 'FULL_BLOCK' | 'PARTIAL_MASK';
  maskedText: string;
}

const syncFilterResultsToContentScript = async (
  videoId: string,
  data: FullAnalysisResponse,
  settings: AppSettings,
) => {
  const entries: FilterEntry[] = data.results
    .map(c => ({ c, decision: derivePolicy(c, settings.intensity) }))
    .filter(
      ({ decision }) =>
        decision.action === 'FULL_BLOCK' || decision.action === 'PARTIAL_MASK',
    )
    .map(({ c, decision }) => ({
      id: c.comment_id,
      textNorm: ultraNormalize(c.text),
      action: decision.action as 'FULL_BLOCK' | 'PARTIAL_MASK',
      maskedText: c.masked_text,
    }));

  if (typeof chrome !== 'undefined' && chrome.storage?.local) {
    await chrome.storage.local.set({
      [FILTER_RESULT_KEY]: { videoId, entries },
    });
  }

  if (typeof chrome !== 'undefined' && chrome.tabs) {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]?.id) {
        chrome.tabs.sendMessage(tabs[0].id, { type: 'FILTER_RESULTS_UPDATED' });
      }
    });
  }
};

// ── YouTube + Text 분석 통합 쿼리 ──
// signature는 keywordModes + 사용자 사전(blacklist/whitelist) 에 의존한다.
// 보안 모드/모듈은 클라이언트 정책 재유도로 처리되므로 queryKey에 포함하지 않는다.
// 사전 변경 시 signature가 바뀌도록 해서 invalidate 누락·팝업 생명주기 이슈와
// 무관하게 항상 재분석을 강제한다.
const buildAnalysisSignature = (
  keywordModes: Record<string, KeywordMode>,
  whitelist: string[],
  blacklist: string[],
): string => {
  const modesKey = Object.entries(keywordModes)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([w, m]) => `${w}:${m}`)
    .join('|');
  const wKey = [...whitelist].sort().join(',');
  const bKey = [...blacklist].sort().join(',');
  return `m:${modesKey || '-'}|w:${wKey}|b:${bKey}`;
};

// YouTube 댓글 수집만 캐시 (설정/모드와 무관 — 비디오 ID 고정 시 영구 캐시)
const useYoutubeComments = (videoId: string | null) => {
  return useQuery<YoutubeAnalysisResponse>({
    queryKey: ['youtube-comments', videoId],
    queryFn: () => fetchAnalysis(videoId!),
    enabled: !!videoId,
    staleTime: Infinity,
    gcTime: 1000 * 60 * 30,
  });
};

export const useFullAnalysis = (
  videoId: string | null,
  keywordModes: Record<string, KeywordMode> = {},
) => {
  const { data: settings } = useSettings();
  const { data: dictionary } = useDictionary();
  const signature = buildAnalysisSignature(
    keywordModes,
    dictionary?.whitelist ?? [],
    dictionary?.blacklist ?? [],
  );

  const { data: youtubeData, isLoading: isYoutubeLoading } = useYoutubeComments(videoId);

  const query = useQuery({
    queryKey: ['full-analysis', videoId, signature],
    queryFn: async () => {
      // 1. chrome.storage.session 캐시 확인 (signature 기반)
      const cached = await loadAnalysisFromStorage(videoId!, signature);
      if (cached) {
        return cached;
      }

      // 2. YouTube 데이터는 별도 쿼리가 이미 가져와 캐시해둔 것 재사용
      if (!youtubeData) {
        throw new Error('youtubeData not loaded yet');
      }

      // 3. 텍스트 분석 API 호출
      const rawComments = youtubeData.results;
      const textResults = await fetchTextAnalysis(rawComments, {
        videoId,
        keywordModes,
      });

      const fullData: FullAnalysisResponse = {
        video_info: youtubeData.video_info,
        total_comments: youtubeData.total_comments,
        results: rawComments.map((raw, i) => ({
          comment_id: raw.comment_id,
          text: raw.text,
          author: raw.author,
          published_at: raw.published_at,
          parent_id: raw.parent_id ?? null,
          masked_text: textResults[i].details.masked_text,
          score: textResults[i].score,
          detected_words: textResults[i].details.detected_words,
          flags: textResults[i].flags,
        } satisfies AnalyzedComment)),
      };

      await saveAnalysisToStorage(videoId!, signature, fullData);
      return fullData;
    },
    enabled: !!videoId && !!youtubeData && !!dictionary,
    staleTime: 1000 * 60 * 5,
    placeholderData: keepPreviousData,
  });

  // data 또는 보안 모드가 바뀔 때마다 content-script에 최신 필터 결과 동기화.
  // 보안 모드 변경은 서버 호출을 트리거하지 않지만, 여기서 derivePolicy 기반으로 다시 동기화한다.
  useEffect(() => {
    if (videoId && query.data && settings) {
      syncFilterResultsToContentScript(videoId, query.data, settings);
    }
  }, [videoId, query.data, settings]);

  return {
    data: query.data ?? null,
    isLoading: isYoutubeLoading || query.isLoading,
    isFetching: query.isFetching,
    isError: query.isError,
  };
};
