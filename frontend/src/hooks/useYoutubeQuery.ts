import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchAnalysis, fetchTextAnalysis } from '../api/services';
import type { AppSettings, AnalyzedComment, FullAnalysisResponse } from '../api/types';

const ANALYSIS_STORAGE_KEY = 'guard-filter-analysis';
const FILTER_RESULT_KEY = 'guard-filter-results';

const CACHE_TTL = 5 * 60 * 1000; // 5분

// ── 텍스트 정규화 (API textOriginal ↔ DOM textContent 차이 대응) ──
// 공백, 줄바꿈, 특수 유니코드 공백을 모두 제거하고 소문자화
function normalizeForMatch(text: string): string {
  return text.replace(/[\s\u200B-\u200D\uFEFF]/g, '').toLowerCase();
}

// ── 팝업 분석 캐시 (chrome.storage.session — 팝업 전용) ──

const saveAnalysisToStorage = async (videoId: string, data: FullAnalysisResponse) => {
  if (typeof chrome !== 'undefined' && chrome.storage?.session) {
    await chrome.storage.session.set({ [ANALYSIS_STORAGE_KEY]: { videoId, data, cachedAt: Date.now() } });
  }
};

const loadAnalysisFromStorage = async (videoId: string): Promise<FullAnalysisResponse | null> => {
  if (typeof chrome !== 'undefined' && chrome.storage?.session) {
    const result = await chrome.storage.session.get(ANALYSIS_STORAGE_KEY);
    const cached = result[ANALYSIS_STORAGE_KEY] as { videoId: string; data: FullAnalysisResponse; cachedAt?: number } | undefined;
    if (cached && cached.videoId === videoId && cached.cachedAt && Date.now() - cached.cachedAt < CACHE_TTL) {
      return cached.data;
    }
  }
  return null;
};

// ── 필터링 결과를 chrome.storage.local에 저장 (content-script 접근 가능) ──

const syncFilterResultsToContentScript = async (videoId: string, data: FullAnalysisResponse) => {
  const filteredTexts = data.results
    .filter(c => c.action !== 'PASS')
    .map(c => normalizeForMatch(c.text));

  // 1. chrome.storage.local에 저장 (content-script가 언제든 읽을 수 있음)
  if (typeof chrome !== 'undefined' && chrome.storage?.local) {
    await chrome.storage.local.set({
      [FILTER_RESULT_KEY]: { videoId, texts: filteredTexts },
    });
  }

  // 2. content-script에 알림 (즉시 반영)
  if (typeof chrome !== 'undefined' && chrome.tabs) {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]?.id) {
        chrome.tabs.sendMessage(tabs[0].id, { type: 'FILTER_RESULTS_UPDATED' });
      }
    });
  }
};

// ── YouTube + Text 분석 통합 쿼리 ──

export const useFullAnalysis = (videoId: string | null) => {
  const query = useQuery({
    queryKey: ['full-analysis', videoId],
    queryFn: async () => {
      // 1. chrome.storage.session 캐시 확인
      const cached = await loadAnalysisFromStorage(videoId!);
      if (cached) {
        await syncFilterResultsToContentScript(videoId!, cached);
        return cached;
      }

      // 2. 캐시 없음 → YouTube 댓글 수집
      const youtubeData = await fetchAnalysis(videoId!);

      // 3. 텍스트 분석 API 호출
      const rawComments = youtubeData.results;
      const textResults = await fetchTextAnalysis(rawComments);

      const fullData: FullAnalysisResponse = {
        video_info: youtubeData.video_info,
        total_comments: youtubeData.total_comments,
        results: rawComments.map((raw, i) => ({
          comment_id: raw.comment_id,
          text: raw.text,
          author: raw.author,
          published_at: raw.published_at,
          processed_text: textResults[i].processed_text,
          action: textResults[i].action,
          score: textResults[i].score,
          detected_words: textResults[i].details.detected_words,
        } satisfies AnalyzedComment)),
      };

      // 4. 저장 + content-script 동기화
      await saveAnalysisToStorage(videoId!, fullData);
      await syncFilterResultsToContentScript(videoId!, fullData);
      return fullData;
    },
    enabled: !!videoId,
    staleTime: 1000 * 60 * 5,
  });

  return {
    data: query.data ?? null,
    isLoading: query.isLoading,
    isError: query.isError,
  };
};

// ── 설정값 관리 ──

const STORAGE_KEY = 'guard-filter-settings';

const defaultSettings: AppSettings = {
  intensity: 3,
  modules: {
    modified: false,
    sexual: false,
    privacy: false,
    aggression: false,
    political: false,
    spam: false,
    family: false,
  },
};

const getSettingsFromStorage = async (): Promise<AppSettings> => {
  if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
    const result = await chrome.storage.local.get(STORAGE_KEY);
    return (result[STORAGE_KEY] as AppSettings) || defaultSettings;
  }
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored ? JSON.parse(stored) : defaultSettings;
};

const saveSettingsToStorage = async (newSettings: AppSettings) => {
  if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
    await chrome.storage.local.set({ [STORAGE_KEY]: newSettings });
  } else {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newSettings));
  }
  return newSettings;
};

export const useSettings = () => {
  return useQuery({
    queryKey: ['app-settings'],
    queryFn: getSettingsFromStorage,
    initialData: defaultSettings,
  });
};

export const useUpdateSettings = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: saveSettingsToStorage,
    onSuccess: (newSettings) => {
      queryClient.setQueryData(['app-settings'], newSettings);
    },
  });
};
