import type { OverlayConfig, OverlayConfigRequest } from '../types/overlay'
import { apiClient } from './client'

export const overlaysApi = {
  /** 단일 활성 오버레이 — 메인/설정 페이지 모두 이걸로 통일 */
  active: async (): Promise<OverlayConfig> => {
    const { data } = await apiClient.get<OverlayConfig>('/overlays/active')
    return data
  },

  updateActive: async (req: OverlayConfigRequest): Promise<OverlayConfig> => {
    const { data } = await apiClient.patch<OverlayConfig>('/overlays/active', req)
    return data
  },

  /** 메인 페이지의 채팅 입력바 — 더미 채널에 1회 주입 */
  injectTest: async (content: string, author = 'Tester'): Promise<{ ok: boolean; injected: boolean }> => {
    const { data } = await apiClient.post('/test/inject', { content, author })
    return data
  },

  /** 치지직 연동 시작 — auth_url 반환. 호출자가 새 창으로 이동. */
  chzzkStart: async (): Promise<{ auth_url: string }> => {
    const { data } = await apiClient.post('/profile/chzzk/start')
    return data
  },

  /** 치지직 연동 상태 */
  chzzkStatus: async (): Promise<{ connected: boolean; expires_at?: string }> => {
    const { data } = await apiClient.get('/profile/chzzk/status')
    return data
  },

  /** 치지직 연동 해제 */
  chzzkDisconnect: async (): Promise<void> => {
    await apiClient.delete('/profile/chzzk')
  },

  list: async (): Promise<OverlayConfig[]> => {
    const { data } = await apiClient.get<OverlayConfig[]>('/overlays')
    return data
  },

  get: async (id: number): Promise<OverlayConfig> => {
    const { data } = await apiClient.get<OverlayConfig>(`/overlays/${id}`)
    return data
  },

  getByToken: async (token: string): Promise<OverlayConfig> => {
    const { data } = await apiClient.get<OverlayConfig>(`/overlays/by-token/${token}`)
    return data
  },

  create: async (req: OverlayConfigRequest): Promise<OverlayConfig> => {
    const { data } = await apiClient.post<OverlayConfig>('/overlays', req)
    return data
  },

  update: async (id: number, req: OverlayConfigRequest): Promise<OverlayConfig> => {
    const { data } = await apiClient.patch<OverlayConfig>(`/overlays/${id}`, req)
    return data
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/overlays/${id}`)
  },
}
