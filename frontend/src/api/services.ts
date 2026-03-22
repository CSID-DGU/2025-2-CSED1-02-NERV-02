import axios from 'axios';
import type { YoutubeAnalysisResponse, SystemConfigResponse, SystemConfigUpdate, DictionaryResponse, DictionaryUpdateResponse } from './types';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// --- API FUNCTIONS ---

// 1. 유튜브 영상 댓글 분석
export const fetchAnalysis = async (userId: number, videoId: string, maxPages: number = 1): Promise<YoutubeAnalysisResponse> => {
  // 로컬 개발 환경이거나 videoId가 테스트용이면 Mock 데이터 반환
  // if (!import.meta.env.PROD || videoId === 'test_video_id') {
  //   console.log(`[Mock API] Fetching analysis for ${videoId}`);
  //   await new Promise((resolve) => setTimeout(resolve, 800)); // 0.8초 딜레이 시뮬레이션
  //   return MOCK_ANALYSIS_DATA;
  // }

  // 실제 API 호출
  const response = await client.post(`/api/users/${userId}/youtube-analyses`, {
    video_id: videoId,
    max_pages: maxPages
  });
  return response.data;
};

// 2. 시스템 설정 조회 (GET)
export const fetchSystemConfig = async (userId: number): Promise<SystemConfigResponse> => {
  const response = await client.get<SystemConfigResponse>(`/api/users/${userId}/settings`);
  return response.data;
};

// 3. 시스템 설정 업데이트 (PATCH)
export const updateSystemConfig = async (userId: number, data: SystemConfigUpdate): Promise<SystemConfigResponse> => {
  const response = await client.patch<SystemConfigResponse>(`/api/users/${userId}/settings`, data);
  return response.data;
};

// 4. 사전 전체 조회 (GET) - whitelist + blacklist 동시 조회
export const fetchDictionary = async (userId: number): Promise<DictionaryResponse> => {
  const response = await client.get<DictionaryResponse>(`/api/users/${userId}/dictionaries`);
  return response.data;
};

// 5. 단어 일괄 추가 (POST)
export const addDictionaryWord = async (userId: number, listType: 'whitelist' | 'blacklist', words: string[]): Promise<DictionaryUpdateResponse> => {
  const response = await client.post<DictionaryUpdateResponse>(
    `/api/users/${userId}/dictionaries/${listType}`,
    { words }
  );
  return response.data;
};

// 6. 단어 목록 일괄 삭제 (DELETE)
export const deleteDictionaryWord = async (userId: number, listType: 'whitelist' | 'blacklist', words: string[]): Promise<DictionaryUpdateResponse> => {
  const response = await client.delete<DictionaryUpdateResponse>(
    `/api/users/${userId}/dictionaries/${listType}`,
    { data: { words } }
  );
  return response.data;
};