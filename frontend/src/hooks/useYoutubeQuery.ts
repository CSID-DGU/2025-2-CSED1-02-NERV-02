import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchAnalysis } from '../api/services';
import type { AppSettings } from '../api/types';

// 1. 유튜브 분석 데이터 쿼리
export const useYoutubeAnalysis = (videoId: string | null) => {
  return useQuery({
    queryKey: ['youtube-analysis', videoId],
    queryFn: () => fetchAnalysis(videoId!),
    enabled: !!videoId,
    staleTime: 1000 * 60,
  });
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