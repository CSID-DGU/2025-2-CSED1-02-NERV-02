import { createContext, useContext, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { overlaysApi } from '../api/overlays'
import { useOverlayWebSocket, type ChatMessage } from '../hooks/useOverlayWebSocket'

/**
 * App 레벨에서 한 번만 활성화되는 채팅 스트림 컨텍스트.
 *
 * 라우트(메인/내정보/설정/히스토리) 가 바뀌어도 App 컴포넌트는 unmount 되지 않으므로
 * 여기서 잡고 있는 WebSocket 연결과 messages 상태가 그대로 유지된다.
 *
 * 새로고침으로 App 자체가 다시 마운트될 때는 useOverlayWebSocket 의
 * sessionStorage 캐시(persistKey) 로 직전 메시지를 복원한다.
 */

interface ChatStreamCtx {
  messages: ChatMessage[]
  allMessages: ChatMessage[]
  state: 'connecting' | 'open' | 'closed' | 'error'
  markRendered: (id: string) => void
  clearCollected: () => void
  overlayToken: string | undefined
}

const Ctx = createContext<ChatStreamCtx | null>(null)

export function ChatStreamProvider({ children }: { children: ReactNode }) {
  const { data: config } = useQuery({
    queryKey: ['overlay-active'],
    queryFn: overlaysApi.active,
  })

  const token = config?.overlay_token
  const persistKey = token ? `chat:${token}` : undefined

  const stream = useOverlayWebSocket(token, {
    max: 50,
    collectAll: true,
    persistKey,
  })

  return (
    <Ctx.Provider value={{ ...stream, overlayToken: token }}>
      {children}
    </Ctx.Provider>
  )
}

export function useChatStream(): ChatStreamCtx {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useChatStream must be used inside <ChatStreamProvider>')
  return ctx
}
