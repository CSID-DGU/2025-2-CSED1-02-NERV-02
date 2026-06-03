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
}

export function useOverlayWebSocket(token: string | undefined, opts: Options = {}) {
  const { max = 30, collectAll = false } = opts
  const [messages, setMessages] = useState<ChatMessage[]>([])
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
      setMessages((prev) => [...prev, msg].slice(-max))
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
  }, [token, max, collectAll])

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
