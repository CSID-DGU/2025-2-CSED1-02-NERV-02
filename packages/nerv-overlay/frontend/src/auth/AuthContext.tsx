import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { authApi, type AuthUser } from '../api/auth'
import { authStorage } from '../api/client'

interface AuthContextValue {
  user: AuthUser | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  register: (username: string, nickname: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  // 부팅 시 토큰 있으면 /me 로 사용자 복원
  useEffect(() => {
    const token = authStorage.get()
    if (!token) {
      setLoading(false)
      return
    }
    authApi
      .me()
      .then((u) => setUser(u))
      .catch(() => authStorage.clear())
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (username: string, password: string) => {
    const res = await authApi.login(username, password)
    authStorage.set(res.token)
    setUser(res.user)
  }, [])

  const register = useCallback(async (username: string, nickname: string, password: string) => {
    const res = await authApi.register(username, nickname, password)
    authStorage.set(res.token)
    setUser(res.user)
  }, [])

  const logout = useCallback(() => {
    authStorage.clear()
    setUser(null)
    // 연동 상태·캐시된 query 가 즉각 반영되도록 홈으로 이동 + 1회 새로고침
    window.location.href = '/'
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
