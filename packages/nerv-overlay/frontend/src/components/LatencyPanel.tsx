import type { LatencyStats, LatencySample } from '../hooks/useLatencyStats'
import { downloadCsv } from '../hooks/useLatencyStats'

interface Props {
  stats: LatencyStats
  samples: LatencySample[]
  overlayName: string
  onClear: () => void
}

export function LatencyPanel({ stats, samples, overlayName, onClear }: Props) {
  const handleExport = () => {
    const ts = new Date().toISOString().replace(/[:.]/g, '-')
    const filename = `latency_${overlayName}_${ts}.csv`
    downloadCsv(samples, filename)
  }

  return (
    <aside className="latency-panel">
      <header className="latency-panel-header">
        <h2>측정 통계</h2>
        <span className="badge">{stats.count} samples</span>
      </header>

      <div className="latency-grid">
        <Metric label="Filter (ms)" dist={stats.filter_ms} />
        <Metric label="Server→Client (ms)" dist={stats.server_to_client_ms} />
        <Metric label="Render (ms)" dist={stats.e2e_render_ms} />
        <Metric label="Total (ms)" dist={stats.total_ms} highlight />
      </div>

      <div className="latency-actions">
        <button onClick={handleExport} className="btn btn-primary" disabled={stats.count === 0}>
          CSV 다운로드 ({stats.count})
        </button>
        <button onClick={onClear} className="btn">
          버퍼 비우기
        </button>
      </div>

      <p className="latency-hint">
        ?debug=1 모드. URL 에서 ?debug=1 빼면 통계 패널이 사라집니다.
      </p>
    </aside>
  )
}

interface MetricProps {
  label: string
  dist: { mean: number; p50: number; p95: number; p99: number; min: number; max: number }
  highlight?: boolean
}

function Metric({ label, dist, highlight }: MetricProps) {
  return (
    <div className={`metric ${highlight ? 'metric-highlight' : ''}`}>
      <div className="metric-label">{label}</div>
      <div className="metric-rows">
        <Row k="mean" v={dist.mean} />
        <Row k="p50"  v={dist.p50} />
        <Row k="p95"  v={dist.p95} />
        <Row k="p99"  v={dist.p99} />
        <Row k="min"  v={dist.min} />
        <Row k="max"  v={dist.max} />
      </div>
    </div>
  )
}

function Row({ k, v }: { k: string; v: number }) {
  return (
    <div className="metric-row">
      <span className="k">{k}</span>
      <span className="v">{v.toFixed(1)}</span>
    </div>
  )
}
