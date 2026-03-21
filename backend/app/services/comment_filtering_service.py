import logging
from app.repositories.user_repository import UserRepository
from app.engines.first_pass_filter import FirstPassFilter
from app.engines.second_pass_filter import SecondPassFilter
from app.engines.risk_scorer import RiskScorer
from app.engines.policy_manager import PolicyManager

logger = logging.getLogger(__name__)

class CommentFilteringService:
    def __init__(
        self,
        user_repo: UserRepository,
        first_pass: FirstPassFilter,
        second_pass: SecondPassFilter,
        scorer: RiskScorer,
        policy: PolicyManager
    ):
        self.user_repo = user_repo
        self.first_pass = first_pass
        self.second_pass = second_pass
        self.scorer = scorer
        self.policy = policy

    async def process_comment(self, user_id: int, comment_text: str) -> dict:
        logger.info(f"유저({user_id}) 댓글 검사 파이프라인 시작")

        user = await self.user_repo.get_user_settings(user_id)
        if not user:
            return {"action": "ERROR", "reason": "USER_NOT_FOUND"}

        await self.first_pass.reload_engine(user_id)

        filter_result = self.first_pass.execute(comment_text)
        # filter_result = self.second_pass.execute(filter_result)
        risk_score = self.scorer.execute(filter_result)
        final_decision = self.policy.decide_action(
            risk_score=risk_score,
            filter_result=filter_result,
            user_security_level=user.security_level,
            user_risk_threshold=user.risk_threshold
        )

        final_decision['details'] = filter_result

        logger.info(f"검사 완료 | 최종 판정: {final_decision['action']}")
        return final_decision