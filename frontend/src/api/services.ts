import axios from 'axios';
import type { YoutubeAnalysisResponse, TextAnalysisResponse, RawComment, SystemConfigResponse, SystemConfigUpdate, DictionaryResponse, DictionaryUpdateResponse, KeywordAnalysisResponse, YoutubeChannelInfo, FilterDictionaryResponse } from './types';

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

// 1. 유튜브 영상 댓글 수집
export const fetchAnalysis = async (videoId: string): Promise<YoutubeAnalysisResponse> => {
  const response = await client.get(`/api/analyses/youtube`, {
    params: { video_id: videoId }
  });
  return response.data;
};


// 1-2. 댓글 필터링 분석
export const fetchTextAnalysis = async (comments: RawComment[]): Promise<TextAnalysisResponse[]> => {
  const response = await client.post<TextAnalysisResponse[]>(`/api/analyses/text`, comments);
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
    `/api/users/dictionaries/${listType.toUpperCase()}`,
    { words }
  );
  return response.data;
};

// 6. 단어 목록 일괄 삭제 (DELETE)
export const deleteDictionaryWord = async (listType: 'whitelist' | 'blacklist', words: string[]): Promise<DictionaryUpdateResponse> => {
  const response = await client.delete<DictionaryUpdateResponse>(
    `/api/users/dictionaries/${listType.toUpperCase()}`,
    { data: { words } }
  );
  return response.data;
};

// 7. 키워드 분석 (POST)
export const fetchKeywordAnalysis = async (comments: RawComment[]): Promise<KeywordAnalysisResponse> => {
  const response = await client.post<KeywordAnalysisResponse>('/api/analyses/keywords', comments);
  return response.data;
};

// 8. YouTube 채널 연동
export const linkYoutubeChannel = async (channelId: string): Promise<YoutubeChannelInfo> => {
  const response = await client.put<YoutubeChannelInfo>('/api/users/youtube-channel', { channel_id: channelId });
  return response.data;
};

// 9. YouTube 채널 연동 해제
export const unlinkYoutubeChannel = async (): Promise<void> => {
  await client.delete('/api/users/youtube-channel');
};

// 10. 클라이언트 필터링용 정규화 사전 조회
export const fetchFilterDictionary = async (): Promise<FilterDictionaryResponse> => {
  const response = await client.get<FilterDictionaryResponse>('/api/users/filter-dictionary');
  return response.data;
};