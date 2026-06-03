import { useEffect, useRef, useState } from 'react'
import { WS_BASE_URL } from '../api/client'

export interface ChatMessage {
  id: string
  author: string
  original_text: string
  masked_text: string
  action: 'NORMAL' | 'REVIEW' | 'PARTIAL_MASK' | 'FULL_BLOCK' | 'ERROR'
  score: number
  detected_words: { word: string; type: string }[]
  ts_generated: number
  ts_filter_start: number
  ts_filter_end: number
  ts_sent: number
  /** 클라이언트 수신 시각 (성능 측정용) */
  ts_received: number
  /** 클라이언트 DOM 렌더 직전 시각 (raf 콜백) */
  ts_rendered?: number
}

type ConnectionState = 'connecting' | 'open' | 'closed' | 'error'

interface Options {
  /** 화면에 유지할 최근 메시지 수 */
  max?: number
  /** 측정용 누적 버퍼 사용 여부 (true 면 모든 메시지 보존) */
  collectAll?: boolean
  /**
   * sessionStorage 캐시 키 — 지정하면 mount 시 복원, 새 메시지마다 저장.
   * 다른 탭/라우트로 이동 후 다시 돌아와도 (또는 새로고침 후) 이전 메시지 유지.
   */
  persistKey?: string
}

const MAX_PERSIST = 100

function readPersisted(key: string): ChatMessage[] {
  try {
    const raw = sessionStorage.getItem(key)
    if (!raw) return []
    const arr = JSON.parse(raw)
    return Array.isArray(arr) ? (arr as ChatMessage[]) : []
  } catch {
    return []
  }
}

function writePersisted(key: string, msgs: ChatMessage[]) {
  try {
    sessionStorage.setItem(key, JSON.stringify(msgs.slice(-MAX_PERSIST)))
  } catch {
    // quota exceeded 등 — 무시
  }
}

export function useOverlayWebSocket(token: string | undefined, opts: Options = {}) {
  const { max = 30, collectAll = false, persistKey } = opts
  const [messages, setMessages] = useState<ChatMessage[]>(() =>
    persistKey ? readPersisted(persistKey).slice(-max) : [],
  )
  const [allMessages, setAllMessages] = useState<ChatMessage[]>([])
  const [state, setState] = useState<ConnectionState>('connecting')
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!token) return

    const url = `${WS_BASE_URL}/ws/overlay/${token}`
    let alive = true
    let ws: WebSocket | null = null
    let reconnectTimer: number | null = null
    let attempts = 0

    const handleMessage = (ev: MessageEvent) => {
      const ts_received = performance.timeOrigin + performance.now()
      const data = JSON.parse(ev.data) as Omit<ChatMessage, 'ts_received'>
      const msg: ChatMessage = { ...data, ts_received }
      setMessages((prev) => {
        const next = [...prev, msg].slice(-max)
        if (persistKey) writePersisted(persistKey, next)
        return next
      })
      if (collectAll) {
        setAllMessages((prev) => [...prev, msg])
      }
    }

    function connect() {
      if (!alive) return
      setState('connecting')
      ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        attempts = 0
        setState('open')
      }
      ws.onclose = () => {
        setState('closed')
        if (!alive) return
        // 끊김 자동 재연결 — 방송 시작/끝, 토큰 갱신, 네트워크 일시 끊김 등에 대비
        // 1s → 2s → 4s → 8s (최대 8초) backoff
        attempts += 1
        const delay = Math.min(8000, 1000 * Math.pow(2, attempts - 1))
        reconnectTimer = window.setTimeout(connect, delay)
      }
      ws.onerror = () => setState('error')
      ws.onmessage = handleMessage
    }

    connect()

    return () => {
      alive = false
      if (reconnectTimer) clearTimeout(reconnectTimer)
      if (ws) ws.close()
    }
  }, [token, max, collectAll, persistKey])

  /** 메시지가 DOM 에 그려진 시각을 기록 (측정용) */
  const markRendered = (id: string) => {
    const ts_rendered = performance.timeOrigin + performance.now()
    setMessages((prev) =>
      prev.map((m) => (m.id === id && !m.ts_rendered ? { ...m, ts_rendered } : m))
    )
    if (collectAll) {
      setAllMessages((prev) =>
        prev.map((m) => (m.id === id && !m.ts_rendered ? { ...m, ts_rendered } : m))
      )
    }
  }

  const clearCollected = () => setAllMessages([])

  return { messages, allMessages, state, markRendered, clearCollected }
}
