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

/**
 * 클라이언트에서 본 "진행 중" 판정 — 백엔드 idle 종료가 늦더라도
 * last_message_at 이 N분 전이면 종료된 것으로 표시.
 */
const CLIENT_ACTIVE_CUTOFF_MS = 3 * 60 * 1000
function displayIsActive(s: BroadcastSession): boolean {
  if (!s.is_active) return false
  if (!s.last_message_at) return true
  const last = new Date(s.last_message_at).getTime()
  return Date.now() - last < CLIENT_ACTIVE_CUTOFF_MS
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
  const isActive = displayIsActive(session)
  return (
    <section className={open ? 'history-block history-block-open' : 'history-block'}>
      <button type="button" className="history-block-head" onClick={onToggle}>
        <div className="history-block-title">
          <span className="history-date">{formatDate(session.started_at)}</span>
          {isActive && <span className="history-live-pill">● 진행 중</span>}
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

  /**
   * 로컬 체크 상태 — 사용자가 자유롭게 토글 가능.
   * 서버에서 이미 selected_for_relearn=true 인 항목은 "lock" 으로 분류돼
   * 체크가 풀리지 않음.
   * 재학습 버튼을 누르면 여기 담긴 ID 들이 서버로 일괄 commit 됨.
   */
  const [pendingIds, setPendingIds] = useState<Set<number>>(new Set())

  /** 재학습 버튼 — 선택된 항목들을 서버에 batch commit → DB 영구 고정 */
  const submitMut = useMutation({
    mutationFn: async (ids: number[]) => {
      const results = await Promise.allSettled(
        ids.map((id) => historyApi.select(id)),
      )
      const failed = results.filter((r) => r.status === 'rejected').length
      return { total: ids.length, failed }
    },
    onSuccess: ({ total, failed }) => {
      setPendingIds(new Set())
      qc.invalidateQueries({ queryKey: ['history-messages', sessionId] })
      if (failed > 0) {
        alert(`${total}건 중 ${failed}건 실패. 다시 시도해 주세요.`)
      } else {
        alert(`${total}건이 재학습 후보로 고정되었습니다.\n(현재 재학습 실행은 아직 활성화되지 않았습니다.)`)
      }
    },
  })

  const lockedCount = useMemo(
    () => messagesQ.data?.filter((m) => m.selected_for_relearn).length ?? 0,
    [messagesQ.data],
  )

  if (messagesQ.isLoading) return <p className="hint" style={{ padding: '12px 16px' }}>불러오는 중...</p>
  if (!messagesQ.data || messagesQ.data.length === 0) {
    return <p className="hint" style={{ padding: '12px 16px' }}>이 방송에서 필터링된 메시지가 없습니다.</p>
  }

  const togglePending = (id: number) => {
    setPendingIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const onSubmit = () => {
    const ids = Array.from(pendingIds)
    if (ids.length === 0) return
    submitMut.mutate(ids)
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
          {messagesQ.data.map((m: FilteredMessage) => {
            const locked = m.selected_for_relearn
            const checked = locked || pendingIds.has(m.id)
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
                    checked={checked}
                    disabled={locked || submitMut.isPending}
                    onChange={() => !locked && togglePending(m.id)}
                    title={locked
                      ? '이미 재학습 후보로 전송된 항목 (해제 불가)'
                      : '재학습 후보로 선택'}
                  />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>

      <div className="history-actions">
        <span className="hint">
          선택 {pendingIds.size}건 · 고정 {lockedCount}건
          {pendingIds.size > 0 && ' (재학습 후 해제 불가)'}
        </span>
        <button
          type="button"
          className="btn btn-primary"
          disabled={pendingIds.size === 0 || submitMut.isPending}
          onClick={onSubmit}
          title={pendingIds.size === 0
            ? '선택된 항목이 없습니다.'
            : '선택한 메시지를 재학습 후보로 전송합니다.'}
        >
          {submitMut.isPending ? '전송 중...' : `🔒 재학습 (${pendingIds.size}건)`}
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
