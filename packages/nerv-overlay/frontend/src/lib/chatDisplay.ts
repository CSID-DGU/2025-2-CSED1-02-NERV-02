import type { ChatMessage } from '../hooks/useOverlayWebSocket'

/**
 * action + block_display_mode 조합으로 채팅의 최종 표시 텍스트 결정.
 * - NORMAL / REVIEW / ERROR → 원문 그대로
 * - PARTIAL_MASK / FULL_BLOCK → block_display_mode 적용:
 *     MASK        → 별표 마스킹된 텍스트
 *     PLACEHOLDER → 대체 문구
 *     HIDE        → 미표시 (hidden=true)
 */
export function resolveDisplay(
  msg: ChatMessage,
  blockMode: string,
  placeholder: string,
): { text: string; hidden: boolean } {
  const blocked = msg.action === 'PARTIAL_MASK' || msg.action === 'FULL_BLOCK'
  if (!blocked) {
    return { text: msg.original_text, hidden: false }
  }
  if (blockMode === 'HIDE') return { text: '', hidden: true }
  if (blockMode === 'PLACEHOLDER') return { text: placeholder, hidden: false }
  return { text: msg.masked_text, hidden: false }
}
