import logging
from app.db.models import User
from app.repositories.dictionary import DictionaryRepository
from .first_pass_filter import FirstPassFilter
from .second_pass_filter import SecondPassFilter
from .risk_scorer import RiskScorer
from .policy_manager import PolicyManager
from app.schemas import FilterResult, TextAnalysisResponse

logger = logging.getLogger(__name__)

class TextAnalysisService:
    def __init__(
        self,
        first_pass: FirstPassFilter,
        second_pass: SecondPassFilter,
        scorer: RiskScorer,
        policy: PolicyManager,
        dict_repo: DictionaryRepository,
    ):
        self.first_pass = first_pass
        self.second_pass = second_pass
        self.scorer = scorer
        self.policy = policy
        self.dict_repo = dict_repo

    def _analyze_single(self, user: User, text: str, dicts) -> TextAnalysisResponse:
        preview = text[:20].replace("\n", " ")
        logger.info(f"댓글(\"{preview}\") 필터링 검사 시작")

        filter_result = self.first_pass.execute(text, dicts.whitelist, dicts.blacklist, dicts.system_dict)

        risk_score = self.scorer.execute(filter_result)
        final_decision = self.policy.decide_action(
            risk_score=risk_score,
            filter_result=filter_result,
            user_security_level=user.security_level,
            user_risk_threshold=user.risk_threshold
        )

        logger.info(f"검사 완료 | 최종 판정: {final_decision['action']}")

        return TextAnalysisResponse(
            original_text=text,
            processed_text=final_decision["processed_text"],
            action=final_decision["action"],
            score=risk_score,
            details=FilterResult.model_validate(filter_result),
        )

    async def analyze_text(self, user: User, text: str) -> TextAnalysisResponse:
        dicts = await self.dict_repo.load_dictionaries(user.id)
        return self._analyze_single(user, text, dicts)

    async def analyze_texts(self, user: User, texts: list[str]) -> list[TextAnalysisResponse]:
        dicts = await self.dict_repo.load_dictionaries(user.id)
        return [self._analyze_single(user, text, dicts) for text in texts]