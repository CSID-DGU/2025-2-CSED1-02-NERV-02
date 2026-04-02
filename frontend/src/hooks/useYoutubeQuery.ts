import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchAnalysis, fetchTextAnalysis } from '../api/services';
import type { AppSettings, AnalyzedComment, FullAnalysisResponse } from '../api/types';

// 1. 유튜브 분석 데이터 쿼리
export const useYoutubeAnalysis = (videoId: string | null) => {
  return useQuery({
    queryKey: ['youtube-analysis', videoId],
    queryFn: () => fetchAnalysis(videoId!),
    enabled: !!videoId,
    staleTime: 1000 * 60,
  });
};


const ANALYSIS_STORAGE_KEY = 'guard-filter-analysis';

const saveAnalysisToStorage = async (videoId: string, data: FullAnalysisResponse) => {
  if (typeof chrome !== 'undefined' && chrome.storage?.session) {
    await chrome.storage.session.set({ [ANALYSIS_STORAGE_KEY]: { videoId, data } });
  }
};

const loadAnalysisFromStorage = async (videoId: string): Promise<FullAnalysisResponse | null> => {
  if (typeof chrome !== 'undefined' && chrome.storage?.session) {
    const result = await chrome.storage.session.get(ANALYSIS_STORAGE_KEY);
    const cached = result[ANALYSIS_STORAGE_KEY] as { videoId: string; data: FullAnalysisResponse } | undefined;
    if (cached && cached.videoId === videoId) return cached.data;
  }
  return null;
};

// 2. YouTube + Text 분석 통합 쿼리
export const useFullAnalysis = (videoId: string | null) => {
  const youtubeQuery = useYoutubeAnalysis(videoId);

  const textQuery = useQuery({
    queryKey: ['text-analysis', videoId],
    queryFn: async () => {
      // 1. 스토리지 캐시 확인
      const cached = await loadAnalysisFromStorage(videoId!);
      if (cached) return cached;

      // 2. API 호출
      const rawComments = youtubeQuery.data!.results;
      const textResults = await fetchTextAnalysis(rawComments);

      const fullData: FullAnalysisResponse = {
        video_info: youtubeQuery.data!.video_info,
        total_comments: youtubeQuery.data!.total_comments,
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

      // 3. 스토리지에 저장
      await saveAnalysisToStorage(videoId!, fullData);
      return fullData;
    },
    enabled: !!youtubeQuery.data,
    staleTime: Infinity,
  });

  return {
    data: textQuery.data ?? null,
    isLoading: youtubeQuery.isLoading || textQuery.isLoading,
    isError: youtubeQuery.isError || textQuery.isError,
  };
};

// 2. 설정값 관리 (Chrome Storage 연동)
// API 서버에 설정 저장 기능이 없으므로, 로컬 스토리지(확장프로그램 스토리지)를 사용합니다.
const STORAGE_KEY = 'guard-filter-settings';

const defaultSettings: AppSettings = {
  intensity: 3,
  modules: {  modified: false,
    sexual: false,
    privacy: false,
    aggression: false,
    political: false,
    spam: false,
    family: false, },
};

// 설정을 불러오는 가짜 비동기 함수
const getSettingsFromStorage = async (): Promise<AppSettings> => {
  if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
    const result = await chrome.storage.local.get(STORAGE_KEY);
    return (result[STORAGE_KEY] as AppSettings) || defaultSettings;
  }
  // 로컬 개발 환경 (localStorage 사용)
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored ? JSON.parse(stored) : defaultSettings;
};

// 설정을 저장하는 가짜 비동기 함수
const saveSettingsToStorage = async (newSettings: AppSettings) => {
  if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
    await chrome.storage.local.set({ [STORAGE_KEY]: newSettings });
  } else {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newSettings));
  }
  return newSettings;
};

// [Hook] 설정 불러오기
export const useSettings = () => {
  return useQuery({
    queryKey: ['app-settings'],
    queryFn: getSettingsFromStorage,
    initialData: defaultSettings,
  });
};

// [Hook] 설정 업데이트하기 (Mutation)
export const useUpdateSettings = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: saveSettingsToStorage,
    onSuccess: (newSettings) => {
      queryClient.setQueryData(['app-settings'], newSettings);
    },
  });
};