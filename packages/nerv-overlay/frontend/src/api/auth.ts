import { apiClient } from './client'

export interface AuthUser {
  id: number
  username: string
  nickname: string
}

export interface AuthResponse {
  token: string
  user: AuthUser
}

export const authApi = {
  register: async (username: string, nickname: string, password: string): Promise<AuthResponse> => {
    const { data } = await apiClient.post<AuthResponse>('/auth/register', { username, nickname, password })
    return data
  },
  login: async (username: string, password: string): Promise<AuthResponse> => {
    const { data } = await apiClient.post<AuthResponse>('/auth/login', { username, password })
    return data
  },
  me: async (): Promise<AuthUser> => {
    const { data } = await apiClient.get<AuthUser>('/auth/me')
    return data
  },
}
