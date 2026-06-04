import logging
from app.db.models import User
from app.repositories.dictionary import DictionaryRepository
from .first_pass_filter import FirstPassFilter
from .second_pass_filter import SecondPassFilter
from .risk_scorer import RiskScorer
from .policy_manager import PolicyManager
from .context import VideoContext
from app.services.active_learning_collector import ActiveLearningCollector
from app.schemas import FilterResult, TextAnalysisResponse, ScorerFlags
from app.schemas.enums import SecurityLevel, ModerationAction

logger = logging.getLogger(__name__)

AI_ATTRIBUTION_THRESHOLD = 0.15
AI_ATTRIBUTION_TOP_K = 10
AI_ATTRIBUTION_FALLBACK_TOP_N = 1

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
        self.al_collector = ActiveLearningCollector()

    def _build_response(
        self,
        user: User,
        text: str,
        filter_result: dict,
        video_context: VideoContext,
    ) -> TextAnalysisResponse:
        scorer_result = self.scorer.execute(filter_result, video_context)

        security_level = SecurityLevel(user.security_level)

        final_decision = self.policy.decide_action(
            scorer_result=scorer_result,
            filter_result=filter_result,
            security_level=SecurityLevel(user.security_level),
            ai_soften_enabled=user.ai_soften_enabled,
        )

        # ──────────────────────────────────────────────
        # AI 탐지 결과에 대한 보안 수준별 후처리
        # LOW    → 원문 유지 + 프론트 경고
        # MEDIUM → Input Gradient 기반 부분 마스킹
        # HIGH   → 전체 차단
        # ──────────────────────────────────────────────
        ai_modules = scorer_result.get("ai_modules", [])

        if ai_modules and final_decision["action"] == ModerationAction.PARTIAL_MASK:
            try:
                masking_result = self.second_pass.mask_by_ai_evidence(
                    text=text,
                    target_modules=ai_modules,
                    attribution_threshold=AI_ATTRIBUTION_THRESHOLD,
                    top_k=AI_ATTRIBUTION_TOP_K,
                    fallback_top_n=AI_ATTRIBUTION_FALLBACK_TOP_N,
                )

                final_decision["processed_text"] = masking_result["processed_text"]

            except Exception as e:
                logger.error(
                    "AI Input Gradient 마스킹 중 오류 발생: %s",
                    e,
                    exc_info=True,
                )

                # 마스킹 실패 시 전체 차단하지 않고 REVIEW로 폴백
                final_decision["processed_text"] = text
                final_decision["action"] = ModerationAction.REVIEW

        preview = text[:20].replace("\n", " ")
        logger.info(
            f'댓글("{preview}") 필터링 결과 | score : {scorer_result["score"]:.2f}'
        )

        return TextAnalysisResponse(
            original_text=text,
            processed_text=final_decision["processed_text"],
            action=final_decision["action"],
            ai_modules=scorer_result.get("ai_modules", []),
            score=scorer_result["score"],
            details=FilterResult.model_validate(filter_result),
            flags=ScorerFlags(
                has_blacklist=scorer_result["has_blacklist"],
                has_general=scorer_result["has_general"],
                has_trigger=scorer_result["has_trigger"],
            ),
        )

    def _build_execution_env(self, user: User, dicts, video_context: VideoContext):
        """FILTER 모드 키워드는 SYSTEM_KEYWORD 로 라우팅 (블랙리스트보다 약한 처분).

        1차 필터는 blacklist/system_dict 두 버킷을 분리해 매칭 결과에 WordType 을
        태깅하므로, 여기서 어느 버킷에 넣느냐가 그대로 scorer 의 카테고리 결정
        (BLACKLIST vs GENERAL) 으로 이어진다.

        IGNORE 키워드는 no-op 이므로 여기서 어느 버킷에도 union 하지 않는다.
        """
        effective_blacklist = set(dicts.blacklist)
        effective_system_dict = set(dicts.system_dict) | set(video_context.filter_keywords)
        effective_whitelist = set(dicts.whitelist)
        dict_version = f"u{user.id}:{len(dicts.blacklist)}:{len(dicts.whitelist)}:{video_context.cache_signature()}"
        return effective_whitelist, effective_blacklist, effective_system_dict, dict_version

    async def analyze_text(
        self,
        user: User,
        text: str,
        video_context: VideoContext | None = None,
    ) -> TextAnalysisResponse:
        ctx = video_context or VideoContext()
        dicts = await self.dict_repo.load_dictionaries(user.id)
        effective_whitelist, effective_blacklist, effective_system_dict, dict_version = self._build_execution_env(user, dicts, ctx)
        filter_result = self.first_pass.execute(
            text, effective_whitelist, effective_blacklist, effective_system_dict, dict_version
        )

        scorer_result = self.scorer.execute(filter_result, ctx)
        if self._should_run_second_pass(user, scorer_result):
            filter_result = await self.second_pass.execute(filter_result, enabled_modules=user.enabled_modules)
            await self.al_collector.collect(user=user, filter_result=filter_result)
        return self._build_response(user, text, filter_result, ctx)

    async def analyze_texts(
        self,
        user: User,
        texts: list[str],
        video_context: VideoContext | None = None,
    ) -> list[TextAnalysisResponse]:
        ctx = video_context or VideoContext()
        dicts = await self.dict_repo.load_dictionaries(user.id)
        effective_whitelist, effective_blacklist, effective_system_dict, dict_version = self._build_execution_env(user, dicts, ctx)

        # Kiwi 배치 토큰화로 1차 필터 일괄 수행
        filter_results = self.first_pass.execute_batch(
            texts, effective_whitelist, effective_blacklist, effective_system_dict, dict_version
        )

        second_pass_results = []

        for fr in filter_results:
            scorer_result = self.scorer.execute(fr, ctx)

            if self._should_run_second_pass(user, scorer_result):
                fr = await self.second_pass.execute(fr, enabled_modules=user.enabled_modules)

            await self.al_collector.collect(user=user, filter_result=fr)

            second_pass_results.append(fr)

        return [
            self._build_response(user, text, fr, ctx)
            for text, fr in zip(texts, second_pass_results)
        ]

    def _should_run_second_pass(self, user: User, scorer_result: dict) -> bool:
        if not user.use_detail_ai_model:
            return False

        if not user.enabled_modules or not user.enabled_modules.strip():
            return False
    
        if scorer_result.get("has_blacklist"):
            return False

        if scorer_result.get("has_trigger"):
            return False
        
        return True