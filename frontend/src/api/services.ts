import axios from 'axios';
import type { YoutubeAnalysisResponse, SystemConfigResponse, SystemConfigUpdate, DictionaryResponse, DictionaryUpdateResponse } from './types';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Axios interceptor - 모든 요청에 토큰 자동 추가
client.interceptors.request.use(
  async (config) => {
    const { access_token } = await chrome.storage.local.get('access_token');
    if (access_token) {
      config.headers.Authorization = `Bearer ${access_token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Axios interceptor - 401 에러 시 토큰 제거
client.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      await chrome.storage.local.remove(['access_token', 'user_id']);
    }
    return Promise.reject(error);
  }
);

// --- AUTH API ---

// 회원가입
export const register = async (username: string, password: string): Promise<{ access_token: string; token_type: string; user_id: number }> => {
  const response = await client.post('/api/auth/register', { username, password });
  return response.data;
};

// 로그인
export const login = async (username: string, password: string): Promise<{ access_token: string; token_type: string; user_id: number }> => {
  const response = await client.post('/api/auth/login', { username, password });
  return response.data;
};

// 현재 사용자 정보 조회
export const getCurrentUser = async (): Promise<{ user_id: number; username: string }> => {
  const response = await client.get('/api/auth/me');
  return response.data;
};

// --- API FUNCTIONS ---

// 1. 유튜브 영상 댓글 분석
export const fetchAnalysis = async (videoId: string, maxPages: number = 1): Promise<YoutubeAnalysisResponse> => {
  // 로컬 개발 환경이거나 videoId가 테스트용이면 Mock 데이터 반환
  // if (!import.meta.env.PROD || videoId === 'test_video_id') {
  //   console.log(`[Mock API] Fetching analysis for ${videoId}`);
  //   await new Promise((resolve) => setTimeout(resolve, 800)); // 0.8초 딜레이 시뮬레이션
  //   return MOCK_ANALYSIS_DATA;
  // }

  // 실제 API 호출
  const response = await client.post(`/api/analyses/youtube`, {
    video_id: videoId,
    max_pages: maxPages
  });
  return response.data;
};

// 2. 시스템 설정 조회 (GET)
export const fetchSystemConfig = async (): Promise<SystemConfigResponse> => {
  const response = await client.get<SystemConfigResponse>(`/api/users/settings`);
  return response.data;
};

// 3. 시스템 설정 업데이트 (PATCH)
export const updateSystemConfig = async (data: SystemConfigUpdate): Promise<SystemConfigResponse> => {
  const response = await client.patch<SystemConfigResponse>(`/api/users/settings`, data);
  return response.data;
};

// 4. 사전 전체 조회 (GET) - whitelist + blacklist 동시 조회
export const fetchDictionary = async (): Promise<DictionaryResponse> => {
  const response = await client.get<DictionaryResponse>(`/api/users/dictionaries`);
  return response.data;
};

// 5. 단어 일괄 추가 (POST)
export const addDictionaryWord = async (listType: 'whitelist' | 'blacklist', words: string[]): Promise<DictionaryUpdateResponse> => {
  const response = await client.post<DictionaryUpdateResponse>(
    `/api/users/dictionaries/${listType}`,
    { words }
  );
  return response.data;
};

// 6. 단어 목록 일괄 삭제 (DELETE)
export const deleteDictionaryWord = async (listType: 'whitelist' | 'blacklist', words: string[]): Promise<DictionaryUpdateResponse> => {
  const response = await client.delete<DictionaryUpdateResponse>(
    `/api/users/dictionaries/${listType}`,
    { data: { words } }
  );
  return response.data;
};