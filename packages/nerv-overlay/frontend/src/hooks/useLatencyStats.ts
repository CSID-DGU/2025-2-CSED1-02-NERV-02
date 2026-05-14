import { useMemo } from 'react'
import type { ChatMessage } from './useOverlayWebSocket'

export interface LatencySample {
  id: string
  action: string
  filter_ms: number          // filter-service 처리
  fetcher_to_filter_ms: number  // chat-fetcher 메시지 도착 ~ filter 시작
  server_to_client_ms: number  // Spring → Browser 전송
  e2e_render_ms: number      // 수신 → DOM 렌더
  total_ms: number           // 메시지 발생 → DOM 표시 (전체)
}

export interface LatencyStats {
  count: number
  filter_ms: Distribution
  total_ms: Distribution
  e2e_render_ms: Distribution
  server_to_client_ms: Distribution
}

interface Distribution {
  mean: number
  p50: number
  p95: number
  p99: number
  min: number
  max: number
}

function buildSample(msg: ChatMessage): LatencySample | null {
  if (msg.ts_rendered === undefined) return null
  return {
    id: msg.id,
    action: msg.action,
    filter_ms: msg.ts_filter_end - msg.ts_filter_start,
    fetcher_to_filter_ms: msg.ts_filter_start - msg.ts_generated,
    server_to_client_ms: msg.ts_received - msg.ts_sent,
    e2e_render_ms: msg.ts_rendered - msg.ts_received,
    total_ms: msg.ts_rendered - msg.ts_generated,
  }
}

function distribution(values: number[]): Distribution {
  if (values.length === 0) {
    return { mean: 0, p50: 0, p95: 0, p99: 0, min: 0, max: 0 }
  }
  const sorted = [...values].sort((a, b) => a - b)
  const sum = sorted.reduce((acc, v) => acc + v, 0)
  return {
    mean: sum / sorted.length,
    p50: sorted[Math.floor(sorted.length * 0.5)],
    p95: sorted[Math.floor(sorted.length * 0.95)],
    p99: sorted[Math.floor(sorted.length * 0.99)],
    min: sorted[0],
    max: sorted[sorted.length - 1],
  }
}

export function useLatencyStats(messages: ChatMessage[]) {
  return useMemo(() => {
    const samples = messages
      .map(buildSample)
      .filter((s): s is LatencySample => s !== null)

    const stats: LatencyStats = {
      count: samples.length,
      filter_ms: distribution(samples.map((s) => s.filter_ms)),
      total_ms: distribution(samples.map((s) => s.total_ms)),
      e2e_render_ms: distribution(samples.map((s) => s.e2e_render_ms)),
      server_to_client_ms: distribution(samples.map((s) => s.server_to_client_ms)),
    }

    return { samples, stats }
  }, [messages])
}

/** 샘플들을 CSV 문자열로 직렬화 */
export function toCsv(samples: LatencySample[]): string {
  const header = 'id,action,filter_ms,fetcher_to_filter_ms,server_to_client_ms,e2e_render_ms,total_ms'
  const rows = samples.map((s) =>
    [s.id, s.action, s.filter_ms, s.fetcher_to_filter_ms, s.server_to_client_ms, s.e2e_render_ms, s.total_ms].join(',')
  )
  return [header, ...rows].join('\n')
}

/** CSV 다운로드 트리거 */
export function downloadCsv(samples: LatencySample[], filename: string): void {
  const csv = toCsv(samples)
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
