export type SecurityLevel = 'LOW' | 'MEDIUM' | 'HIGH'
export type BlockDisplayMode = 'MASK' | 'HIDE' | 'PLACEHOLDER'
export type ChatSource = 'DUMMY' | 'CHZZK' | 'YOUTUBE'

export interface OverlayConfig {
  id: number
  overlay_token: string
  overlay_url: string
  name: string
  channel_id: string | null
  channel_name: string | null
  source: ChatSource
  security_level: SecurityLevel
  block_display_mode: BlockDisplayMode
  placeholder_text: string
  show_score: boolean
  whitelist: string[]
  blacklist: string[]
  created_at: string
  updated_at: string
}

export interface OverlayConfigRequest {
  name?: string
  channel_id?: string | null
  source?: ChatSource
  security_level?: SecurityLevel
  block_display_mode?: BlockDisplayMode
  placeholder_text?: string
  show_score?: boolean
  whitelist?: string[]
  blacklist?: string[]
}
