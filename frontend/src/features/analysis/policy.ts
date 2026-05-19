import type { AnalyzedComment, ModerationAction, SecurityLevel } from '../../api/types';

// 백엔드 PolicyManager와 동일한 매트릭스 (policy_manager.py _MATRIX 미러).
// 보안 모드 변경 시 서버 재호출 없이 action/displayText를 재유도하기 위해 미러링.
type Category = 'BLACKLIST' | 'GENERAL_TRIGGER' | 'GENERAL';

const MATRIX: Record<SecurityLevel, Record<Category, ModerationAction>> = {
  LOW: {
    BLACKLIST: 'PARTIAL_MASK',
    GENERAL_TRIGGER: 'PARTIAL_MASK',
    GENERAL: 'REVIEW',
  },
  MEDIUM: {
    BLACKLIST: 'FULL_BLOCK',
    GENERAL_TRIGGER: 'PARTIAL_MASK',
    GENERAL: 'PARTIAL_MASK',
  },
  HIGH: {
    BLACKLIST: 'FULL_BLOCK',
    GENERAL_TRIGGER: 'FULL_BLOCK',
    GENERAL: 'PARTIAL_MASK',
  },
};

const AI_MATRIX: Record<SecurityLevel, ModerationAction> = {
  LOW: 'REVIEW',
  MEDIUM: 'FULL_BLOCK',
  HIGH: 'FULL_BLOCK',
};

export interface DerivedDecision {
  action: ModerationAction;
  processed_text: string;
  score: number;
}

// 서버 base score 에 보안수준 가산(+25)을 적용한 display score.
// Caution 버킷(SYSTEM 전용): MEDIUM·HIGH 에서 +25 (MEDIUM 도 이제 PARTIAL_MASK 로 처분됨)
// Warn 버킷(BLACKLIST): MEDIUM·HIGH 에서 +25
// 보안수준 변경 시 서버 재호출 없이 즉시 반응하도록 클라이언트에서 계산한다.
const applySecurityAdjustment = (
  baseScore: number,
  comment: AnalyzedComment,
  securityLevel: SecurityLevel,
): number => {
  const hasAiModules = (comment.ai_modules ?? []).length > 0;

  if (!comment.detected_words.length && !hasAiModules) {
    return baseScore;
  }

  let bonus = 0;

  if (hasAiModules) {
    if (securityLevel === 'HIGH') bonus = 0.25;
  } else if (comment.flags.has_blacklist) {
    if (securityLevel === 'MEDIUM' || securityLevel === 'HIGH') bonus = 0.25;
  } else if (comment.flags.has_general) {
    if (securityLevel === 'MEDIUM' || securityLevel === 'HIGH') bonus = 0.25;
  }

  return Math.min(1.0, baseScore + bonus);
};

export const derivePolicy = (
  comment: AnalyzedComment,
  securityLevel: SecurityLevel,
): DerivedDecision => {
  const score = applySecurityAdjustment(comment.score, comment, securityLevel);
  const hasAiModules = (comment.ai_modules ?? []).length > 0;

  // 2차 AI 탐지 결과
  // AI는 특정 단어 위치를 모르므로 PARTIAL_MASK를 사용하지 않는다.
  if (hasAiModules) {
    const action = AI_MATRIX[securityLevel];

    return {
      action,
      processed_text: action === 'FULL_BLOCK' ? '' : comment.text,
      score,
    };
  }
  
  if (!comment.detected_words.length) {
    return { action: 'NORMAL', processed_text: comment.text, score };
  }

  // detected_words 가 존재하면 어느 카테고리로든 분류되어야 한다.
  // 플래그가 모두 false 로 돌아오는 엣지케이스(신규 WordType 등)는 GENERAL 로 폴백.
  const category: Category = comment.flags.has_blacklist
    ? 'BLACKLIST'
    : comment.flags.has_trigger
    ? 'GENERAL_TRIGGER'
    : 'GENERAL';

  const action = MATRIX[securityLevel][category];
  const processed_text =
    action === 'FULL_BLOCK' ? '' : action === 'PARTIAL_MASK' ? comment.masked_text : comment.text;

  return { action, processed_text, score };
};
