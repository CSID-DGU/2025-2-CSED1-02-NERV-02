import { Outlet } from 'react-router-dom'
import { AppNav } from './components/AppNav'
import { ChatStreamProvider } from './stream/ChatStreamProvider'

/**
 * 일반 페이지 레이아웃 — 상단 네비 + 라우트 컨텐츠.
 *
 * 여기 ChatStreamProvider 를 두면, 사용자가 메인→설정→내정보→히스토리 사이를
 * 오가도 채팅 WS 연결과 수집된 메시지가 유지된다 (App 자체는 unmount 되지 않음).
 */
export function App() {
  return (
    <ChatStreamProvider>
      <AppNav />
      <Outlet />
    </ChatStreamProvider>
  )
}
