import { useMemo, useState } from 'react';
import { useAnalysisContext } from '../../features/analysis/AnalysisContext';
import { useSettings } from '../../hooks/useSystemConfig';
import { derivePolicy } from '../../features/analysis/policy';
import type { AnalyzedComment, ModerationAction } from '../../api/types';

type ActionStyle = {
  bg: string;
  avatar: string;
  textClass: string;
  badgeBg: string;
  badgeLabel: string;
};

const ACTION_STYLES: Record<ModerationAction, ActionStyle> = {
  FULL_BLOCK: {
    bg: 'bg-red-50',
    avatar: 'bg-red-400',
    textClass: 'text-red-500 italic text-xs',
    badgeBg: 'bg-red-500',
    badgeLabel: '차단',
  },
  PARTIAL_MASK: {
    bg: 'bg-orange-50',
    avatar: 'bg-orange-400',
    textClass: 'text-orange-700',
    badgeBg: 'bg-orange-500',
    badgeLabel: '마스킹',
  },
  REVIEW: {
    bg: 'bg-yellow-50',
    avatar: 'bg-yellow-400',
    textClass: 'text-yellow-800',
    badgeBg: 'bg-yellow-500',
    badgeLabel: '검토',
  },
  NORMAL: {
    bg: 'hover:bg-gray-50',
    avatar: 'bg-indigo-400',
    textClass: 'text-gray-700',
    badgeBg: 'bg-green-500',
    badgeLabel: '정상',
  },
  ERROR: {
    bg: 'bg-gray-50',
    avatar: 'bg-gray-400',
    textClass: 'text-gray-500',
    badgeBg: 'bg-gray-400',
    badgeLabel: '오류',
  },
};

interface CommentRowProps {
  comment: AnalyzedComment;
  action: ModerationAction;
  processedText: string;
  displayScore: number;
  revealed: boolean;
  onToggleReveal: () => void;
  replyCount?: number;
  repliesExpanded?: boolean;
  onToggleReplies?: () => void;
}

const AI_MODULE_LABELS: Record<string, string> = {
  spam: '스팸',
  pii: '개인정보',
  politics: '정치',
  criticism: '비난/협박',
  basic: '기본 유해',
  sexual: '성적',
};

const CommentRow = ({
  comment,
  action,
  processedText,
  displayScore,
  revealed,
  onToggleReveal,
  replyCount,
  repliesExpanded,
  onToggleReplies,
}: CommentRowProps) => {
  const style = ACTION_STYLES[action] ?? ACTION_STYLES.NORMAL;
  const isFullBlock = action === 'FULL_BLOCK';
  const isPartialMask = action === 'PARTIAL_MASK';
  const isReview = action === 'REVIEW';
  const isUserBlacklist = comment.detected_words.some(d => d.type === 'USER_BLACKLIST');
  const aiModules = comment.ai_modules ?? [];
  const hasAiModules = aiModules.length > 0;
  
  return (
    <div className={`flex items-start space-x-3 p-2 rounded-lg transition-colors ${style.bg}`}>
      <div className={`w-10 h-10 rounded-full shrink-0 flex items-center justify-center text-white font-bold text-xs ${style.avatar}`}>
        {comment.author.substring(1, 3).toUpperCase()}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center space-x-2">
          <span className="font-bold text-sm text-gray-800 truncate">{comment.author}</span>
          <span className="text-xs text-gray-400">{comment.published_at}</span>
          {action !== 'NORMAL' && (
            <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold text-white ${style.badgeBg}`}>
              {style.badgeLabel} {Math.round(displayScore * 100)}%
            </span>
          )}
        </div>

        <p className={`text-sm mt-1 leading-relaxed break-words ${style.textClass}`}>
          {isFullBlock ? (
            revealed ? (
              <span>{comment.text}</span>
            ) : (
              <span className="flex items-center">
                <span className="mr-1">🚫</span>
                {isUserBlacklist
                  ? '사용자 블랙리스트 단어가 포함되어 숨겨졌습니다.'
                  : hasAiModules
                    ? 'AI 필터에 의해 숨겨진 댓글입니다.'
                    : '필터링된 댓글입니다.'}
              </span>
            )
          ) : isPartialMask ? (
            processedText
          ) : (
            comment.text
          )}
        </p>

        {isFullBlock && (
          <button
            onClick={onToggleReveal}
            className="text-[10px] mt-1 px-2 py-0.5 bg-gray-200 text-gray-500 rounded hover:bg-gray-300 transition-colors"
          >
            {revealed ? '숨기기' : '원본 보기'}
          </button>
        )}

        {isReview && (
          <div className="flex items-center gap-1 mt-1">
            <span className="text-[10px] px-1.5 py-0.5 bg-yellow-200 text-yellow-800 rounded font-medium">
              사용자 검토가 필요합니다
            </span>
          </div>
        )}

        {displayScore > 0 && (
          <div className="mt-1.5 flex items-center gap-2">
            <div className="w-20 bg-gray-200 rounded-full h-1.5">
              <div
                className={`h-1.5 rounded-full transition-all duration-300 ${style.badgeBg}`}
                style={{ width: `${Math.min(displayScore * 100, 100)}%` }}
              />
            </div>
            <span className="text-[10px] text-gray-400">{displayScore.toFixed(2)}</span>
          </div>
        )}

        {hasAiModules && (
          <div className="flex flex-wrap gap-1 mt-2">
            {aiModules.map((module) => (
              <span
                key={module}
                className="text-[10px] px-1.5 py-0.5 bg-purple-100 text-purple-700 rounded font-medium"
              >
                AI 감지: {AI_MODULE_LABELS[module] ?? module}
              </span>
            ))}
          </div>
        )}

        {comment.detected_words.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {comment.detected_words.map(({ word, type: tag }) => (
              <span key={`${word}-${tag}`} className="text-[10px] px-1.5 py-0.5 bg-gray-200 text-gray-600 rounded font-medium">
                {word} ({tag === 'SYSTEM_KEYWORD' ? '시스템' : '블랙리스트'})
              </span>
            ))}
          </div>
        )}

        {replyCount !== undefined && replyCount > 0 && onToggleReplies && (
          <button
            onClick={onToggleReplies}
            className="text-[10px] mt-2 px-2 py-0.5 bg-blue-50 text-blue-600 rounded hover:bg-blue-100 transition-colors"
          >
            {repliesExpanded ? `답글 ${replyCount}개 숨기기 ▲` : `답글 ${replyCount}개 보기 ▼`}
          </button>
        )}
      </div>
    </div>
  );
};

const ChatTab = () => {
  const { data: analysisData, isLoading, isError, errorMsg } = useAnalysisContext();
  const { data: settings } = useSettings();
  const [revealedIds, setRevealedIds] = useState<Set<string>>(new Set());
  const [expandedReplies, setExpandedReplies] = useState<Set<string>>(new Set());

  // 정책 재유도 + 답글 트리 구성
  const { topLevel, repliesByParent, decisions } = useMemo(() => {
    const topLevel: AnalyzedComment[] = [];
    const repliesByParent = new Map<string, AnalyzedComment[]>();
    const decisions = new Map<string, { action: ModerationAction; processed_text: string; score: number }>();

    if (!analysisData || !settings) {
      return { topLevel, repliesByParent, decisions };
    }

    for (const c of analysisData.results) {
      decisions.set(c.comment_id, derivePolicy(c, settings.intensity));
      if (c.parent_id) {
        const arr = repliesByParent.get(c.parent_id) ?? [];
        arr.push(c);
        repliesByParent.set(c.parent_id, arr);
      } else {
        topLevel.push(c);
      }
    }
    return { topLevel, repliesByParent, decisions };
  }, [analysisData, settings]);

  const toggleReveal = (id: string) => {
    setRevealedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleReplies = (id: string) => {
    setExpandedReplies(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  if (errorMsg) return <div className="p-4 text-center text-gray-500">{errorMsg}</div>;
  if (isLoading) return <div className="p-8 text-center">분석 중입니다... 🛡️</div>;
  if (isError || !analysisData) return <div className="p-4 text-center text-red-500">데이터를 불러오는데 실패했습니다.</div>;

  return (
    <div className="flex flex-col space-y-4 p-2">
      {topLevel.map((comment) => {
        const dec = decisions.get(comment.comment_id) ?? { action: 'NORMAL' as ModerationAction, processed_text: comment.text, score: comment.score };
        const replies = repliesByParent.get(comment.comment_id) ?? [];
        const isExpanded = expandedReplies.has(comment.comment_id);

        return (
          <div key={comment.comment_id} className="flex flex-col">
            <CommentRow
              comment={comment}
              action={dec.action}
              processedText={dec.processed_text}
              displayScore={dec.score}
              revealed={revealedIds.has(comment.comment_id)}
              onToggleReveal={() => toggleReveal(comment.comment_id)}
              replyCount={replies.length}
              repliesExpanded={isExpanded}
              onToggleReplies={replies.length > 0 ? () => toggleReplies(comment.comment_id) : undefined}
            />

            {isExpanded && replies.length > 0 && (
              <div className="ml-10 mt-2 flex flex-col space-y-2 border-l-2 border-gray-200 pl-3">
                {replies.map((reply) => {
                  const rdec = decisions.get(reply.comment_id) ?? { action: 'NORMAL' as ModerationAction, processed_text: reply.text, score: reply.score };
                  return (
                    <CommentRow
                      key={reply.comment_id}
                      comment={reply}
                      action={rdec.action}
                      processedText={rdec.processed_text}
                      displayScore={rdec.score}
                      revealed={revealedIds.has(reply.comment_id)}
                      onToggleReveal={() => toggleReveal(reply.comment_id)}
                    />
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
      {topLevel.length === 0 && (
        <div className="text-center text-gray-400 text-xs py-10">
          표시할 댓글이 없습니다.
        </div>
      )}
    </div>
  );
};

export default ChatTab;
