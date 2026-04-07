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
  user_id: number;
  security_level: number;
  risk_threshold: number;
  use_detail_ai_model: boolean;
  enabled_modules: string;
  youtube_channel_id: string | null;
  youtube_channel_name: string | null;
  youtube_channel_url: string | null;
  youtube_thumbnail_url: string | null;
}

export interface YoutubeChannelInfo {
  channel_id: string;
  channel_name: string;
  channel_url: string;
  thumbnail_url: string | null;
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

export interface FilteredKeyword {
  word: string;
  count: number;
  type: string;
}

export interface TrendingKeyword {
  word: string;
  count: number;
}

export interface KeywordAnalysisResponse {
  filtered_keywords: FilteredKeyword[];
  trending_keywords: TrendingKeyword[];
}

export interface FilterDictionaryResponse {
  patterns: Record<string, { original: string; type: string }>;
  whitelist: string[];
  version: string;
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