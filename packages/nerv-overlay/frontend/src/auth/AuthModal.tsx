import { useEffect, useState } from 'react'
import { useAuth } from './AuthContext'

type Mode = 'login' | 'register'

interface Props {
  open: boolean
  onClose: () => void
  initialMode?: Mode
}

export function AuthModal({ open, onClose, initialMode = 'login' }: Props) {
  const { login, register } = useAuth()
  const [mode, setMode] = useState<Mode>(initialMode)
  const [username, setUsername] = useState('')
  const [nickname, setNickname] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open) {
      setMode(initialMode)
      setUsername('')
      setNickname('')
      setPassword('')
      setError(null)
      setBusy(false)
    }
  }, [open, initialMode])

  if (!open) return null

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      if (mode === 'login') {
        await login(username.trim(), password)
      } else {
        const nick = nickname.trim() || username.trim()
        await register(username.trim(), nick, password)
      }
      onClose()
    } catch (e: any) {
      setError(e?.response?.data?.message || e?.message || '요청 실패')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-tabs">
          <button
            type="button"
            className={mode === 'login' ? 'modal-tab active' : 'modal-tab'}
            onClick={() => setMode('login')}
          >
            로그인
          </button>
          <button
            type="button"
            className={mode === 'register' ? 'modal-tab active' : 'modal-tab'}
            onClick={() => setMode('register')}
          >
            회원가입
          </button>
        </div>

        <form onSubmit={submit} className="modal-form">
          <label>
            <span>아이디</span>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              minLength={3}
              maxLength={40}
              required
              autoFocus
            />
          </label>

          {mode === 'register' && (
            <label>
              <span>닉네임</span>
              <input
                type="text"
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                placeholder="비워두면 아이디와 동일"
                maxLength={40}
              />
            </label>
          )}

          <label>
            <span>비밀번호</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              minLength={6}
              maxLength={100}
              required
            />
          </label>

          {error && <p className="error" style={{ margin: 0 }}>{error}</p>}

          <div className="modal-actions">
            <button type="button" className="btn" onClick={onClose} disabled={busy}>
              취소
            </button>
            <button type="submit" className="btn btn-primary" disabled={busy}>
              {busy ? '처리 중…' : mode === 'login' ? '로그인' : '회원가입'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
