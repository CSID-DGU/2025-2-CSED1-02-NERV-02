import { apiClient } from './client'

export interface ChzzkOAuthStatus {
  connected: boolean
  expires_at?: string
  expired?: boolean
}

export const oauthApi = {
  chzzkStatus: async (): Promise<ChzzkOAuthStatus> => {
    const { data } = await apiClient.get<ChzzkOAuthStatus>('/oauth/chzzk/status')
    return data
  },
  /** OAuth 시작 — 브라우저를 redirect 시킴 */
  chzzkStartUrl: (): string => '/api/oauth/chzzk/start',
}
