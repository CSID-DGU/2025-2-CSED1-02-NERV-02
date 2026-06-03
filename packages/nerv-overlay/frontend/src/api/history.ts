import { apiClient } from './client'

export interface BroadcastSession {
  id: number
  source: string
  channel_id: string | null
  started_at: string
  ended_at: string | null
  message_count: number
  filtered_count: number
  is_active: boolean
}

export interface FilteredMessage {
  id: number
  author: string
  original_text: string
  masked_text: string | null
  action: string
  score: number
  detected_words: string | null   // "word|type,word|type"
  selected_for_relearn: boolean
  created_at: string
}

export const historyApi = {
  sessions: async (): Promise<BroadcastSession[]> => {
    const { data } = await apiClient.get<BroadcastSession[]>('/history/sessions')
    return data
  },
  messages: async (sessionId: number): Promise<FilteredMessage[]> => {
    const { data } = await apiClient.get<FilteredMessage[]>(`/history/sessions/${sessionId}/messages`)
    return data
  },
  select: async (messageId: number): Promise<FilteredMessage> => {
    const { data } = await apiClient.post<FilteredMessage>(`/history/messages/${messageId}/select`)
    return data
  },
}
