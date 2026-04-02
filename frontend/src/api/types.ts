export interface RawComment {
  comment_id: string;
  text: string;
  author: string;
  published_at: string;
}

export interface YoutubeAnalysisResponse {
  video_info: {
    title: string;
    id: string;
  };
  total_comments: number;
  results: RawComment[];
}

export type ModerationAction = 'PASS' | 'MASKING' | 'REVIEW_HUMAN' | 'AUTO_HIDE' | 'PERMANENT_DELETE';

export interface TextAnalysisResponse {
  original_text: string;
  processed_text: string;
  action: ModerationAction;
  score: number;
  details: {
    original_text: string;
    status: string;
    detected_words: { word: string; type: string }[];
    masked_text: string;
  };
}

export interface AnalyzedComment {
  comment_id: string;
  text: string;
  author: string;
  published_at: string;
  processed_text: string;
  action: ModerationAction;
  score: number;
  detected_words: { word: string; type: string }[];
}

export interface FullAnalysisResponse {
  video_info: { title: string; id: string };
  total_comments: number;
  results: AnalyzedComment[];
}

export interface SystemConfigResponse {
  user_id: number;              // 유저 ID 추가
  security_level: number;       // UI의 intensity (1~5)
  risk_threshold: number;       // 위험도 임계값
  use_detail_ai_model: boolean; // 정밀 AI 사용 여부
  enabled_modules: string;      // 콤마 구분 문자열 (예: "SEXUAL,AGGRESSION" 또는 "ALL")
}

export interface SystemConfigUpdate {
  security_level?: number | null;
  risk_threshold?: number | null;
  use_detail_ai_model?: boolean | null;
  enabled_modules?: string | null;        // string[] -> string
}

export interface AppSettings {
  intensity: number; // 1~5
  modules: {
    modified: boolean;   // MODIFIED
    sexual: boolean;     // SEXUAL
    privacy: boolean;    // PRIVACY
    aggression: boolean; // AGGRESSION
    political: boolean;  // POLITICAL
    spam: boolean;       // SPAM
    family: boolean;     // FAMILY
  };
}

export interface DictionaryRequest {
  words: string[];
  list_type: 'whitelist' | 'blacklist';
}

export interface DictionaryResponse {
  whitelist?: string[]; 
  blacklist?: string[]; 
  total_count: number;
}

export interface DictionaryUpdateResponse {
  status: string;
  message: string;
  processed_count: number;
  current_total: {
    [key: string]: number;
  };
}