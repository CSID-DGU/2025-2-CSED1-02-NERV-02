import axios from 'axios'

const TOKEN_KEY = 'nerv.auth.token'

/** Spring 백엔드 base URL. dev/prod 모두 env 로 주입 (.env.development 가 dev default). */
export const BACKEND_BASE_URL: string = import.meta.env.VITE_BACKEND_BASE_URL || ''

if (!BACKEND_BASE_URL) {
  // eslint-disable-next-line no-console
  console.warn('[nerv] VITE_BACKEND_BASE_URL 미설정 — API/WS 호출이 실패할 수 있습니다.')
}

export const apiClient = axios.create({
  baseURL: `${BACKEND_BASE_URL}/api`,
  headers: { 'Content-Type': 'application/json' },
  timeout: 10000,
})

/** ws:// 또는 wss:// scheme 의 backend URL */
export const WS_BASE_URL: string = BACKEND_BASE_URL.replace(/^http/i, 'ws')

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const authStorage = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}
