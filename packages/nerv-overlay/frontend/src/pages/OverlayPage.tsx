import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { overlaysApi } from '../api/overlays'
import { useOverlayWebSocket, type ChatMessage } from '../hooks/useOverlayWebSocket'
import { resolveDisplay } from '../lib/chatDisplay'

/**
 * OBS Browser Source 가 로드하는 페이지.
 * 깨끗한 채팅 오버레이만 표시. 측정 통계는 /measure/{token} 페이지에서.
 */
export function OverlayPage() {
  const { token } = useParams<{ token: string }>()

  const { data: config } = useQuery({
    queryKey: ['overlay-by-token', token],
    queryFn: () => overlaysApi.getByToken(token!),
    enabled: !!token,
  })

  const { messages, state, markRendered } = useOverlayWebSocket(token, { max: 30 })

  if (!config) return <div className="overlay-loading">설정 로딩...</div>

  return (
    <div className="overlay-root">
      <div className="overlay-header">
        <strong>{config.name}</strong> · {config.security_level} · {state}
      </div>
      <div className="overlay-message-list">
        {messages.map((m) => (
          <ChatLine
            key={m.id}
            msg={m}
            mode={config.block_display_mode}
            placeholder={config.placeholder_text}
            showScore={config.show_score}
            onRendered={() => markRendered(m.id)}
          />
        ))}
      </div>
    </div>
  )
}

interface ChatLineProps {
  msg: ChatMessage
  mode: string
  placeholder: string
  showScore: boolean
  onRendered: () => void
}

function ChatLine({ msg, mode, placeholder, showScore, onRendered }: ChatLineProps) {
  const reportedRef = useRef(false)

  useEffect(() => {
    if (reportedRef.current) return
    reportedRef.current = true
    requestAnimationFrame(() => onRendered())
  }, [msg, onRendered])

  const { text: display, hidden } = resolveDisplay(msg, mode, placeholder)
  if (hidden) return null

  const className = `chat-line action-${msg.action.toLowerCase()}`
  return (
    <div className={className}>
      <div className="chat-line-author">
        {msg.author}
        {showScore && (
          <span className="chat-line-score">위험도 {Math.round(msg.score * 100)}</span>
        )}
      </div>
      <div className="chat-line-text">{display}</div>
    </div>
  )
}
