import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// API/WS 는 axios + WebSocket 이 VITE_BACKEND_BASE_URL 로 직접 호출 (CORS 는 Spring 이 허용).
// dev/prod 모두 동일 흐름이라 proxy 불필요.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
})
