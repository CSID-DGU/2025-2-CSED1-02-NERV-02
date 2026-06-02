export interface RawComment {
  comment_id: string;
  text: string;
  author: string;
  published_at: string;
  parent_id?: string | null;
}

export interface VideoInfo {
  title: string;
  id: string;
  tags: string[];
  category: string | null;
  topics: string[];
}

export interface YoutubeAnalysisResponse {
  video_info: VideoInfo;
  total_comments: number;
  results: RawComment[];
}

export type AiModuleKey = 'spam' | 'pii' | 'politics' | 'criticism' | 'basic' | 'sexual';

export type AiModules = Record<AiModuleKey, boolean>;

export type SecurityLevel = 'LOW' | 'MEDIUM' | 'HIGH';

export type ModerationAction = 'NORMAL' | 'REVIEW' | 'PARTIAL_MASK' | 'FULL_BLOCK' | 'ERROR';

export type KeywordMode = 'IGNORE' | 'FILTER' | 'TRIGGER';

export interface ScorerFlags {
  has_blacklist: boolean;
  has_general: boolean;
  has_trigger: boolean;
}

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
  flags: ScorerFlags;
  ai_modules?: string[];
}

export interface AnalyzeTextsRequest {
  comments: RawComment[];
  video_id?: string | null;
  keyword_modes?: Record<string, KeywordMode>;
}

export interface AnalyzedComment {
  comment_id: string;
  text: string;
  author: string;
  published_at: string;
  parent_id?: string | null;
  masked_text: string;
  score: number;
  detected_words: { word: string; type: string }[];
  flags: ScorerFlags;
  ai_modules?: string[];
}

export interface FullAnalysisResponse {
  video_info: VideoInfo;
  total_comments: number;
  results: AnalyzedComment[];
}

export interface SystemConfigResponse {
  user_id: number;
  security_level: SecurityLevel;
  ai_soften_enabled: boolean;
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
  security_level?: SecurityLevel | null;
  ai_soften_enabled?: boolean | null;
  use_detail_ai_model?: boolean | null;
  enabled_modules?: string | null;
}

export interface AppSettings {
  intensity: SecurityLevel;
  aiSoftenEnabled: boolean;
  useDetailAiModel: boolean;
  modules: AiModules;
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
