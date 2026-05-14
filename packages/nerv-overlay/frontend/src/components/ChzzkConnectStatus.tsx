import { useQuery } from '@tanstack/react-query'
import { oauthApi } from '../api/oauth'

/**
 * 치지직 OAuth 연동 상태 표시 + 연동 버튼.
 * source=CHZZK 일 때만 노출.
 */
export function ChzzkConnectStatus() {
  const { data, isLoading } = useQuery({
    queryKey: ['chzzk-status'],
    queryFn: oauthApi.chzzkStatus,
    refetchInterval: 5000,
  })

  if (isLoading) return <div className="chzzk-status">상태 확인 중...</div>

  if (!data?.connected) {
    return (
      <div className="chzzk-status not-connected">
        <span>⚠️ 치지직 미연동 — CHZZK source 사용 시 필수</span>
        <a href={oauthApi.chzzkStartUrl()} className="btn btn-primary">치지직 연동</a>
      </div>
    )
  }

  if (data.expired) {
    return (
      <div className="chzzk-status expired">
        <span>⚠️ 토큰 만료 — 재연동 필요</span>
        <a href={oauthApi.chzzkStartUrl()} className="btn btn-primary">재연동</a>
      </div>
    )
  }

  return (
    <div className="chzzk-status connected">
      <span>✅ 치지직 연동됨</span>
      <small>만료: {new Date(data.expires_at!).toLocaleString()}</small>
      <a href={oauthApi.chzzkStartUrl()} className="btn-tiny">재연동</a>
    </div>
  )
}
