import { useEffect, useState } from 'react'
import { Link, Navigate, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../auth/AuthContext'
import { overlaysApi } from '../api/overlays'

/**
 * OBS Browser Source 의 "Custom CSS" 필드에 붙여넣어 송출 화면에 최적화하는 스타일.
 * - 페이지 배경 투명 (방송 화면 위에 올림)
 * - 헤더 숨김
 * - 채팅 버블 가독성 (반투명 검정 + 흰 텍스트 + 텍스트 그림자)
 */
const OBS_CUSTOM_CSS = `/* NERV Overlay — OBS Browser Source Custom CSS */
html, body {
  background: transparent !important;
  margin: 0 !important;
  overflow: hidden !important;
}
.overlay-root { background: transparent !important; }
.overlay-header { display: none !important; }
.overlay-message-list { padding: 8px !important; }
.chat-line {
  background: rgba(0, 0, 0, 0.65) !important;
  border-radius: 12px !important;
  padding: 8px 14px !important;
  margin-bottom: 6px !important;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
}
.chat-line-author {
  color: #ffffff !important;
  font-weight: 700 !important;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.9);
}
.chat-line-text {
  color: #ffffff !important;
  font-size: 15px !important;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.9);
}`

export function ProfilePage() {
  const { user, loading, logout } = useAuth()
  const qc = useQueryClient()
  const [params, setParams] = useSearchParams()
  const [flash, setFlash] = useState<{ kind: 'ok' | 'err'; msg: string } | null>(null)

  const chzzkStatus = useQuery({
    queryKey: ['chzzk-status'],
    queryFn: overlaysApi.chzzkStatus,
    enabled: !!user,
  })
  const overlay = useQuery({
    queryKey: ['overlay-active'],
    queryFn: overlaysApi.active,
    enabled: !!user,
  })

  const startMut = useMutation({
    mutationFn: overlaysApi.chzzkStart,
    onSuccess: ({ auth_url }) => {
      // 같은 창에서 이동 — 콜백이 /profile?chzzk=connected 로 돌아옴
      window.location.href = auth_url
    },
    onError: (e: any) => {
      setFlash({ kind: 'err', msg: e?.response?.data?.message || e?.message || '인가 URL 발급 실패' })
    },
  })
  const disconnectMut = useMutation({
    mutationFn: overlaysApi.chzzkDisconnect,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['chzzk-status'] })
      qc.invalidateQueries({ queryKey: ['overlay-active'] })
      setFlash({ kind: 'ok', msg: '치지직 연동을 해제했습니다.' })
    },
  })

  // OAuth 콜백 결과 처리
  useEffect(() => {
    const result = params.get('chzzk')
    if (!result) return
    if (result === 'connected') {
      setFlash({ kind: 'ok', msg: '치지직 연동 완료! 본인 채널의 채팅을 받아 필터링합니다.' })
      qc.invalidateQueries({ queryKey: ['chzzk-status'] })
      qc.invalidateQueries({ queryKey: ['overlay-active'] })
    } else if (result === 'error') {
      setFlash({ kind: 'err', msg: `치지직 연동 실패: ${params.get('msg') || 'unknown'}` })
    }
    // URL 정리
    params.delete('chzzk')
    params.delete('msg')
    setParams(params, { replace: true })
  }, [params, qc, setParams])

  if (loading) {
    return <div className="page"><p>로딩 중...</p></div>
  }
  if (!user) {
    return <Navigate to="/" replace />
  }

  const connected = !!chzzkStatus.data?.connected
  const channelId = overlay.data?.channel_id
  const channelName = overlay.data?.channel_name
  const isChzzkSource = overlay.data?.source === 'CHZZK'

  return (
    <div className="page">
      <header className="header">
        <div>
          <h1>내정보</h1>
          <p className="hint" style={{ marginTop: 4 }}>
            계정 정보와 채팅 소스 연동을 관리합니다.
          </p>
        </div>
        <Link to="/" className="btn">← 메인으로</Link>
      </header>

      {flash && (
        <div className={flash.kind === 'ok' ? 'flash flash-ok' : 'flash flash-err'}>
          {flash.msg}
          <button type="button" className="flash-close" onClick={() => setFlash(null)}>×</button>
        </div>
      )}

      <section className="profile-section">
        <h2 className="section-title">계정</h2>
        <div className="profile-grid">
          <div className="profile-row">
            <span className="profile-label">아이디</span>
            <span className="profile-value">{user.username}</span>
          </div>
          <div className="profile-row">
            <span className="profile-label">닉네임</span>
            <span className="profile-value">{user.nickname}</span>
          </div>
        </div>
        <div style={{ marginTop: 16 }}>
          <button type="button" className="btn" onClick={logout}>로그아웃</button>
        </div>
      </section>

      <section className="profile-section">
        <h2 className="section-title">채팅 소스 연동</h2>
        <p className="hint" style={{ marginBottom: 12 }}>
          연동하면 메인 화면이 더미 채팅 대신 실제 채팅을 받아 필터링합니다.
        </p>
        <div className="service-connect-grid">
          {/* 치지직 */}
          <div className={connected ? 'service-card service-card-connected service-card-chzzk' : 'service-card service-card-disconnected'}>
            <div className="service-card-header">
              <span className="service-card-name">치지직</span>
              {connected
                ? <span className="service-state-pill state-on">● 연동됨</span>
                : <span className="service-state-pill state-off">○ 미연동</span>
              }
            </div>
            {connected && isChzzkSource && (channelName || channelId) && (
              <div className="service-card-meta">
                {channelName
                  ? <>채널: <strong>{channelName}</strong></>
                  : <>채널 ID: <code>{channelId!.slice(0, 16)}…</code></>}
              </div>
            )}
            <div className="service-card-actions">
              {connected ? (
                <button
                  type="button"
                  className="btn"
                  onClick={() => disconnectMut.mutate()}
                  disabled={disconnectMut.isPending}
                >
                  {disconnectMut.isPending ? '해제 중…' : '연동 해제'}
                </button>
              ) : (
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => startMut.mutate()}
                  disabled={startMut.isPending}
                >
                  {startMut.isPending ? '이동 중…' : '치지직으로 로그인'}
                </button>
              )}
            </div>
          </div>

          {/* YouTube — 보류 */}
          <div className="service-card service-card-disconnected" aria-disabled>
            <div className="service-card-header">
              <span className="service-card-name">YouTube</span>
              <span className="service-state-pill state-off">○ 준비 중</span>
            </div>
            <div className="service-card-meta" style={{ color: 'var(--color-text-faint)' }}>
              곧 지원 예정입니다.
            </div>
            <div className="service-card-actions">
              <button type="button" className="btn" disabled>곧 지원</button>
            </div>
          </div>
        </div>
      </section>

      {/* ── OBS Browser Source — 송출 화면에 채팅 오버레이 ── */}
      {overlay.data && (
        <section className="profile-section">
          <h2 className="section-title">OBS Browser Source</h2>
          <p className="hint" style={{ marginBottom: 14 }}>
            OBS Studio → Sources → + → Browser 로 추가한 뒤, 아래 URL 과 Custom CSS 를 붙여넣으세요.
          </p>

          <div className="obs-block">
            <div className="obs-label">URL</div>
            <div className="url-row">
              <code>{overlay.data.overlay_url}</code>
              <button
                type="button"
                className="btn-tiny"
                onClick={() => {
                  navigator.clipboard.writeText(overlay.data!.overlay_url)
                  setFlash({ kind: 'ok', msg: 'URL 을 클립보드에 복사했습니다.' })
                }}
              >
                복사
              </button>
            </div>
          </div>

          <div className="obs-block">
            <div className="obs-label">Custom CSS <span>· 투명 배경 + 가독성 (선택)</span></div>
            <div className="obs-css-row">
              <pre className="obs-css-pre">{OBS_CUSTOM_CSS}</pre>
              <button
                type="button"
                className="btn-tiny obs-css-copy"
                onClick={() => {
                  navigator.clipboard.writeText(OBS_CUSTOM_CSS)
                  setFlash({ kind: 'ok', msg: 'Custom CSS 를 클립보드에 복사했습니다.' })
                }}
              >
                복사
              </button>
            </div>
            <p className="hint" style={{ marginTop: 6 }}>
              OBS Browser Source 속성 창의 <strong>Custom CSS</strong> 칸에 붙여넣으면 배경이 투명해지고 채팅이 또렷하게 보입니다.
            </p>
          </div>

          <div className="quick-links" style={{ marginTop: 14 }}>
            <Link to={`/overlay/${overlay.data.overlay_token}`} target="_blank" className="btn">
              오버레이 미리보기
            </Link>
          </div>
        </section>
      )}
    </div>
  )
}
