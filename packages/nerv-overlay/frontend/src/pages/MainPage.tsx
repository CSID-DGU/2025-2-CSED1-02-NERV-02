import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { overlaysApi } from '../api/overlays'
import { useOverlayWebSocket, type ChatMessage } from '../hooks/useOverlayWebSocket'
import { useLatencyStats } from '../hooks/useLatencyStats'
import { LatencyGauge } from '../components/LatencyGauge'
import { useAuth } from '../auth/AuthContext'
import { resolveDisplay } from '../lib/chatDisplay'

const SECURITY_LABEL: Record<string, { name: string; desc: string }> = {
  LOW:    { name: '관대',  desc: '경미한 욕설은 통과' },
  MEDIUM: { name: '기본',  desc: '대부분 욕설 마스킹' },
  HIGH:   { name: '엄격',  desc: '의심 표현도 차단' },
}
const BLOCK_LABEL: Record<string, string> = {
  MASK: '별표 마스킹',
  HIDE: '완전 숨김',
  PLACEHOLDER: '대체 문구',
}

export function MainPage() {
  const { user } = useAuth()
  const { data: config, isLoading } = useQuery({
    queryKey: ['overlay-active'],
    queryFn: overlaysApi.active,
  })

  const { messages, allMessages, state, markRendered, clearCollected } =
    useOverlayWebSocket(config?.overlay_token, { max: 50, collectAll: true })

  const { samples, stats } = useLatencyStats(allMessages)

  if (isLoading || !config) {
    return <div className="page"><p>로딩 중...</p></div>
  }

  const isDummyMode = config.source === 'DUMMY'
  const sec = SECURITY_LABEL[config.security_level] ?? SECURITY_LABEL.MEDIUM

  // 표시용 이름 — 로그인 시 닉네임 사용, 비로그인은 '더미테스트'
  const displayName = user ? `${user.nickname}님의 채팅창` : '더미테스트'

  return (
    <div className="page main-page">
      <div className="main-hero">
        <div className="main-hero-left">
          <h1 className="main-hero-title">{displayName}</h1>
          <p className="main-hero-sub">
            {isDummyMode
              ? '더미 채팅이 자동으로 흐릅니다. 아래 채팅바로 직접 메시지를 보내 필터링 결과를 확인할 수 있어요.'
              : '치지직 채널에서 실시간으로 채팅을 받아 필터링합니다.'}
          </p>
        </div>
        <div className="main-hero-cards">
          <div className="hero-card">
            <div className="hero-card-label">보안 강도</div>
            <div className="hero-card-value">
              <span className={`badge badge-${config.security_level.toLowerCase()}`}>
                {config.security_level}
              </span>
              <strong>{sec.name}</strong>
            </div>
            <div className="hero-card-sub">{sec.desc}</div>
          </div>
          <div className="hero-card">
            <div className="hero-card-label">차단 방식</div>
            <div className="hero-card-value">
              <strong>{BLOCK_LABEL[config.block_display_mode] ?? config.block_display_mode}</strong>
            </div>
            <div className="hero-card-sub">
              {config.block_display_mode === 'PLACEHOLDER' && `"${config.placeholder_text}"`}
              {config.block_display_mode === 'MASK' && '욕설 위치를 ***로 표시'}
              {config.block_display_mode === 'HIDE' && '메시지 자체를 미표시'}
            </div>
          </div>
          <div className="hero-card">
            <div className="hero-card-label">연동 서비스</div>
            <div className="hero-card-value">
              {isDummyMode ? (
                <strong style={{ color: 'var(--color-text-muted)' }}>미연동</strong>
              ) : (
                <strong>{config.source === 'CHZZK' ? '치지직' : 'YouTube'}</strong>
              )}
              <span className={`state state-${state}`}>● {state}</span>
            </div>
            <div className="hero-card-sub" style={{ display: 'flex', gap: 6, marginTop: 6 }}>
              {config.source === 'CHZZK' && (
                <span className="service-chip service-chzzk" title="치지직 연동됨">
                  <span className="service-dot" /> 치지직
                </span>
              )}
              {config.source === 'YOUTUBE' && (
                <span className="service-chip service-youtube" title="YouTube 연동됨">
                  <span className="service-dot" /> YouTube
                </span>
              )}
              {isDummyMode && (
                <span style={{ color: 'var(--color-text-faint)', fontSize: 11 }}>
                  내정보에서 치지직/YouTube 연동 가능
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="main-grid">
        <section className="main-feed">
          <div className="main-feed-header">
            <h2 className="section-title" style={{ margin: 0 }}>라이브 채팅</h2>
            <span className="badge" style={{ background: 'var(--color-surface-alt)', color: 'var(--color-text-muted)' }}>
              {messages.length}건
            </span>
          </div>
          <ChatList
            messages={messages}
            onRendered={markRendered}
            blockMode={config.block_display_mode}
            placeholder={config.placeholder_text}
          />
          {isDummyMode && <ChatInputBar />}
        </section>

        <aside className="main-stats">
          <LatencyGauge
            stats={stats}
            samples={samples}
            overlayName={config.name}
            onClear={clearCollected}
          />
        </aside>
      </div>
    </div>
  )
}

interface ChatListProps {
  messages: ChatMessage[]
  onRendered: (id: string) => void
  blockMode: string
  placeholder: string
}

function ChatList({ messages, onRendered, blockMode, placeholder }: ChatListProps) {
  const listRef = useRef<HTMLDivElement>(null)
  const stickToBottomRef = useRef(true)

  // 사용자가 위로 스크롤하면 자동 스크롤 비활성, 다시 바닥이면 활성
  const handleScroll = () => {
    const el = listRef.current
    if (!el) return
    const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
    stickToBottomRef.current = distFromBottom < 40
  }

  // 메시지 추가될 때마다 (필요시) 바닥으로
  useLayoutEffect(() => {
    if (!stickToBottomRef.current) return
    const el = listRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages])

  return (
    <div className="main-message-list" ref={listRef} onScroll={handleScroll}>
      {messages.length === 0 && <p className="empty-list">메시지 대기 중...</p>}
      {messages.map((m) => (
        <ChatLine
          key={m.id}
          msg={m}
          onRendered={() => onRendered(m.id)}
          blockMode={blockMode}
          placeholder={placeholder}
        />
      ))}
    </div>
  )
}

interface ChatLineProps {
  msg: ChatMessage
  onRendered: () => void
  blockMode: string
  placeholder: string
}

function ChatLine({ msg, onRendered, blockMode, placeholder }: ChatLineProps) {
  const reportedRef = useRef(false)
  useEffect(() => {
    if (reportedRef.current) return
    reportedRef.current = true
    requestAnimationFrame(() => onRendered())
  }, [msg, onRendered])

  const { text: display, hidden } = resolveDisplay(msg, blockMode, placeholder)
  if (hidden) return null

  const className = `chat-line action-${msg.action.toLowerCase()}`

  return (
    <div className={className}>
      <div className="chat-line-author">{msg.author}</div>
      <div className="chat-line-text">{display}</div>
      {msg.detected_words.length > 0 && (
        <div className="chat-line-detected">
          {msg.detected_words.map((d) => d.word).join(', ')}
        </div>
      )}
    </div>
  )
}

function ChatInputBar() {
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const content = text.trim()
    if (!content) return
    setBusy(true)
    setError(null)
    try {
      await overlaysApi.injectTest(content)
      setText('')
    } catch (e: any) {
      setError(e?.response?.data?.error || e?.message || '주입 실패')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="chat-input-bar">
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="여기에 텍스트를 입력해 필터링 테스트…"
        maxLength={200}
        disabled={busy}
      />
      <button type="submit" className="btn btn-primary" disabled={busy || !text.trim()}>
        {busy ? '전송 중…' : '보내기'}
      </button>
      {error && <p className="error" style={{ marginTop: 8, width: '100%' }}>{error}</p>}
    </form>
  )
}
