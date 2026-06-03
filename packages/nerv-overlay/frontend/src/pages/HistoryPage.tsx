import { useMemo, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../auth/AuthContext'
import { historyApi, type BroadcastSession, type FilteredMessage } from '../api/history'

export function HistoryPage() {
  const { user, loading } = useAuth()
  const [openSessionId, setOpenSessionId] = useState<number | null>(null)

  const sessionsQ = useQuery({
    queryKey: ['history-sessions'],
    queryFn: historyApi.sessions,
    enabled: !!user,
  })

  if (loading) return <div className="page"><p>로딩 중...</p></div>
  if (!user) return <Navigate to="/" replace />

  return (
    <div className="page">
      <header className="header">
        <div>
          <h1>히스토리</h1>
          <p className="hint" style={{ marginTop: 4 }}>
            방송별로 필터링된 메시지를 모아 두었습니다. 재학습에 보낼 메시지를 선택하세요.
          </p>
        </div>
        <Link to="/" className="btn">← 메인으로</Link>
      </header>

      {sessionsQ.isLoading && <p className="hint">불러오는 중...</p>}
      {sessionsQ.data && sessionsQ.data.length === 0 && (
        <section className="profile-section">
          <p className="hint" style={{ margin: 0 }}>
            아직 기록된 방송이 없습니다. 치지직 연동 후 방송을 진행하면 자동으로 보관됩니다.
          </p>
        </section>
      )}

      <div className="history-blocks">
        {sessionsQ.data?.map((s) => (
          <SessionBlock
            key={s.id}
            session={s}
            open={openSessionId === s.id}
            onToggle={() => setOpenSessionId(openSessionId === s.id ? null : s.id)}
          />
        ))}
      </div>
    </div>
  )
}

function SessionBlock({
  session,
  open,
  onToggle,
}: {
  session: BroadcastSession
  open: boolean
  onToggle: () => void
}) {
  return (
    <section className={open ? 'history-block history-block-open' : 'history-block'}>
      <button type="button" className="history-block-head" onClick={onToggle}>
        <div className="history-block-title">
          <span className="history-date">{formatDate(session.started_at)}</span>
          {session.is_active && <span className="history-live-pill">● 진행 중</span>}
        </div>
        <div className="history-block-meta">
          <span>총 {session.message_count.toLocaleString()}건</span>
          <span className="history-filtered-count">필터링 {session.filtered_count.toLocaleString()}건</span>
          <span className="history-block-toggle">{open ? '▾' : '▸'}</span>
        </div>
      </button>

      {open && <SessionMessages sessionId={session.id} />}
    </section>
  )
}

function SessionMessages({ sessionId }: { sessionId: number }) {
  const qc = useQueryClient()
  const messagesQ = useQuery({
    queryKey: ['history-messages', sessionId],
    queryFn: () => historyApi.messages(sessionId),
  })

  // 낙관적 갱신 — 한 번 선택하면 영구히 true 유지
  const selectMut = useMutation({
    mutationFn: (id: number) => historyApi.select(id),
    onMutate: async (id) => {
      const key = ['history-messages', sessionId]
      await qc.cancelQueries({ queryKey: key })
      const prev = qc.getQueryData<FilteredMessage[]>(key)
      qc.setQueryData<FilteredMessage[]>(key, (old) =>
        (old ?? []).map((m) => (m.id === id ? { ...m, selected_for_relearn: true } : m)),
      )
      return { prev }
    },
    onError: (_e, _id, ctx) => {
      if (ctx?.prev) qc.setQueryData(['history-messages', sessionId], ctx.prev)
    },
  })

  const selectedCount = useMemo(
    () => messagesQ.data?.filter((m) => m.selected_for_relearn).length ?? 0,
    [messagesQ.data],
  )

  if (messagesQ.isLoading) return <p className="hint" style={{ padding: '12px 16px' }}>불러오는 중...</p>
  if (!messagesQ.data || messagesQ.data.length === 0) {
    return <p className="hint" style={{ padding: '12px 16px' }}>이 방송에서 필터링된 메시지가 없습니다.</p>
  }

  return (
    <div className="history-messages">
      <table className="history-table">
        <thead>
          <tr>
            <th>시각</th>
            <th>닉네임</th>
            <th>내용</th>
            <th>판정</th>
            <th style={{ textAlign: 'center' }}>선택</th>
          </tr>
        </thead>
        <tbody>
          {messagesQ.data.map((m) => {
            const locked = m.selected_for_relearn
            return (
              <tr key={m.id} className={locked ? 'history-row-locked' : ''}>
                <td className="history-time">{formatTime(m.created_at)}</td>
                <td className="history-author">{m.author}</td>
                <td className="history-content">{m.original_text}</td>
                <td className="history-action">
                  <span className={`history-pill action-${m.action.toLowerCase()}`}>{m.action}</span>
                </td>
                <td style={{ textAlign: 'center' }}>
                  <input
                    type="checkbox"
                    checked={locked}
                    disabled={locked || selectMut.isPending}
                    onChange={() => !locked && selectMut.mutate(m.id)}
                    title={locked ? '이미 선택된 항목 (영구 유지)' : '재학습 후보로 선택'}
                  />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>

      <div className="history-actions">
        <span className="hint">선택 {selectedCount}건 (한 번 선택하면 해제할 수 없습니다)</span>
        <button
          type="button"
          className="btn btn-primary"
          disabled
          title="재학습 기능은 아직 활성화되지 않았습니다."
        >
          🔒 재학습
        </button>
      </div>
    </div>
  )
}

function formatDate(iso: string) {
  const d = new Date(iso)
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const mi = String(d.getMinutes()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd} ${hh}:${mi}`
}

function formatTime(iso: string) {
  const d = new Date(iso)
  const hh = String(d.getHours()).padStart(2, '0')
  const mi = String(d.getMinutes()).padStart(2, '0')
  const ss = String(d.getSeconds()).padStart(2, '0')
  return `${hh}:${mi}:${ss}`
}
