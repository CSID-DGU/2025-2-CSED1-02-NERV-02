import { Outlet } from 'react-router-dom'
import { AppNav } from './components/AppNav'

/** 일반 페이지 레이아웃 — 상단 네비 + 라우트 컨텐츠 */
export function App() {
  return (
    <>
      <AppNav />
      <Outlet />
    </>
  )
}
