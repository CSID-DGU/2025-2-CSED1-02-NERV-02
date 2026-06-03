import { useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { AuthModal } from '../auth/AuthModal'

export function AppNav() {
  const { pathname } = useLocation()
  const { user, loading, logout } = useAuth()
  const [authOpen, setAuthOpen] = useState(false)
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login')

  const openLogin = () => { setAuthMode('login'); setAuthOpen(true) }
  const openRegister = () => { setAuthMode('register'); setAuthOpen(true) }

  return (
    <>
      <nav className="app-nav">
        <div className="app-nav-inner">
          <Link to="/" className="app-logo">
            <img src="/icons/GuardFilterLogo_48.png" alt="" className="app-logo-img" />
            <span>GuardFilter</span>
          </Link>
          <div className="app-nav-spacer" />

          {!loading && (user ? (
            <>
              {/* 순서: 내정보 → 히스토리 → 설정 → 로그아웃 */}
              <NavLink
                to="/profile"
                className={pathname === '/profile' ? 'btn btn-primary' : 'btn'}
                title={`${user.nickname} (${user.username})`}
              >
                👤 내정보
              </NavLink>
              <NavLink
                to="/history"
                className={pathname.startsWith('/history') ? 'btn btn-primary' : 'btn'}
              >
                📜 히스토리
              </NavLink>
              <NavLink
                to="/settings"
                className={pathname === '/settings' ? 'btn btn-primary' : 'btn'}
              >
                ⚙ 설정
              </NavLink>
              <button type="button" className="btn" onClick={logout}>
                로그아웃
              </button>
            </>
          ) : (
            <>
              <NavLink
                to="/settings"
                className={pathname === '/settings' ? 'btn btn-primary' : 'btn'}
              >
                ⚙ 설정
              </NavLink>
              <button type="button" className="btn" onClick={openLogin}>
                로그인
              </button>
              <button type="button" className="btn btn-primary" onClick={openRegister}>
                회원가입
              </button>
            </>
          ))}
        </div>
      </nav>

      <AuthModal open={authOpen} onClose={() => setAuthOpen(false)} initialMode={authMode} />
    </>
  )
}
