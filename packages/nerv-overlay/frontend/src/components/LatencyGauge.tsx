import type { LatencyStats, LatencySample } from '../hooks/useLatencyStats'
import { downloadCsv } from '../hooks/useLatencyStats'

interface Props {
  stats: LatencyStats
  samples: LatencySample[]
  overlayName: string
  onClear: () => void
}

/**
 * 시각적 지연 표시기. 숫자 나열 대신 게이지 + 한 줄 평가로 일반 사용자도 직관적으로.
 */
export function LatencyGauge({ stats, samples, overlayName, onClear }: Props) {
  const handleExport = () => {
    const ts = new Date().toISOString().replace(/[:.]/g, '-')
    downloadCsv(samples, `latency_${overlayName}_${ts}.csv`)
  }

  // 핵심 지표: total_ms (사용자 인지 지연)
  const totalP50 = stats.total_ms.p50
  const verdict = grade(totalP50)

  return (
    <div className="gauge-panel">
      <div className="gauge-header">
        <h2>지연 측정</h2>
        <span className="badge gauge-count">{stats.count}</span>
      </div>

      {stats.count === 0 ? (
        <div className="gauge-empty">
          <p>채팅이 들어오면 측정이 시작됩니다.</p>
        </div>
      ) : (
        <>
          {/* 메인 게이지 */}
          <div className={`gauge-main grade-${verdict.grade}`}>
            <div className="gauge-main-label">평균 응답 (p50)</div>
            <div className="gauge-main-value">
              <strong>{totalP50.toFixed(0)}</strong>
              <span>ms</span>
            </div>
            <div className="gauge-main-verdict">{verdict.text}</div>
            <div className="gauge-bar">
              <div
                className="gauge-bar-fill"
                style={{ width: `${Math.min(100, (totalP50 / 200) * 100)}%` }}
              />
              <div className="gauge-bar-tick" style={{ left: '15%' }}><span>30</span></div>
              <div className="gauge-bar-tick" style={{ left: '50%' }}><span>100</span></div>
              <div className="gauge-bar-tick" style={{ left: '85%' }}><span>170+</span></div>
            </div>
          </div>

          {/* 단계별 분해 */}
          <div className="gauge-breakdown">
            <Bar label="필터링" valueMs={stats.filter_ms.p50} maxMs={50} color="indigo" />
            <Bar label="네트워크" valueMs={stats.server_to_client_ms.p50} maxMs={50} color="cyan" />
            <Bar label="화면 렌더" valueMs={stats.e2e_render_ms.p50} maxMs={50} color="emerald" />
          </div>

          {/* 안정성 */}
          <div className="gauge-stability">
            <div className="gauge-row">
              <span>최선 (min)</span>
              <strong>{stats.total_ms.min.toFixed(0)}ms</strong>
            </div>
            <div className="gauge-row">
              <span>중앙값 (p50)</span>
              <strong>{stats.total_ms.p50.toFixed(0)}ms</strong>
            </div>
            <div className="gauge-row">
              <span>상위 5% (p95)</span>
              <strong>{stats.total_ms.p95.toFixed(0)}ms</strong>
            </div>
            <div className="gauge-row">
              <span>최악 (max)</span>
              <strong>{stats.total_ms.max.toFixed(0)}ms</strong>
            </div>
          </div>
        </>
      )}

      <div className="gauge-actions">
        <button onClick={handleExport} className="btn btn-primary" disabled={stats.count === 0}>
          CSV 저장
        </button>
        <button onClick={onClear} className="btn">버퍼 비우기</button>
      </div>
    </div>
  )
}

interface BarProps {
  label: string
  valueMs: number
  maxMs: number
  color: 'indigo' | 'cyan' | 'emerald'
}

function Bar({ label, valueMs, maxMs, color }: BarProps) {
  const pct = Math.min(100, (valueMs / maxMs) * 100)
  return (
    <div className={`bar-row bar-${color}`}>
      <div className="bar-label">{label}</div>
      <div className="bar-track">
        <div className="bar-fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="bar-value">{valueMs.toFixed(0)}ms</div>
    </div>
  )
}

function grade(p50: number): { grade: 'great' | 'good' | 'fair' | 'poor'; text: string } {
  if (p50 < 30)  return { grade: 'great', text: '🚀 거의 즉시' }
  if (p50 < 100) return { grade: 'good',  text: '✓ 매우 빠름' }
  if (p50 < 200) return { grade: 'fair',  text: '○ 양호' }
  return { grade: 'poor', text: '⚠ 느림 — 네트워크 점검 필요' }
}
