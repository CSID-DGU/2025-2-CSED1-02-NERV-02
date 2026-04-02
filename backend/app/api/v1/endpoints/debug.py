from fastapi import APIRouter, HTTPException, Body, Depends, Query
import logging

from app.schemas import (
    TextAnalysisRequest, FilterResult,
    RiskResponse, PolicyRequest, PolicyResponse
)
from app.api.deps import (
    get_first_pass_filter, get_second_pass_filter,
    get_risk_scorer, get_policy_manager, get_youtube_analysis_service,
    get_dictionary_repository
)
from app.repositories.dictionary import DictionaryRepository

from app.services.filtering.first_pass_filter import FirstPassFilter
from app.services.filtering.second_pass_filter import SecondPassFilter
from app.services.filtering.risk_scorer import RiskScorer
from app.services.filtering.policy_manager import PolicyManager
from app.services.youtube_analysis_service import YoutubeAnalysisService

router = APIRouter()
logger = logging.getLogger(__name__)

# =========================================================
# [API] 개별 모듈 테스트 (Unit APIs)
# =========================================================

@router.post("/users/{user_id}/first-pass", response_model=FilterResult, summary="Step 1. 1차 필터링")
async def run_first_pass(
    user_id: int,
    input_data: TextAnalysisRequest,
    first_filter: FirstPassFilter = Depends(get_first_pass_filter),
    dict_repo: DictionaryRepository = Depends(get_dictionary_repository)
):
    try:
        dicts = await dict_repo.load_dictionaries(user_id)
        result = first_filter.execute(input_data.text, dicts.whitelist, dicts.blacklist, dicts.system_dict)
        return result
    except KeyError:
        raise HTTPException(status_code=404, detail=f"유저 ID {user_id}를 찾을 수 없습니다.")
    except Exception as e:
        logger.exception("1차 필터링 중 예상치 못한 오류 발생")
        raise HTTPException(status_code=500, detail="서버 내부 오류가 발생했습니다.")
    
@router.post("/second-pass", response_model=FilterResult, summary="Step 2. 2차 필터링 (AI)")
async def run_second_pass(
    first_pass_result: FilterResult = Body(
        ...,
        # [입력 예시] 1차 필터 결과 모델을 그대로 사용 (욕설만 잡힌 상태)
        json_schema_extra={
            "example": {
                "original_text": "야이 개새끼야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라",
                "status": "FILTERED_BY_FIRST_PASS",
                "detected_words": [{"word": "개새끼", "type": "SYSTEM_KEYWORD"}],
                "masked_text": "야이 __F__야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라"
            }
        }
    ),
    second_filter: SecondPassFilter = Depends(get_second_pass_filter)
):
    """
    1차 필터링 결과(FirstPassResponse)를 입력받아 AI 정밀 분석을 수행합니다.
    반환값은 SecondPassResponse 모델을 따르며, AI 적발 내역이 누적됩니다.
    """
    try:
        result = await second_filter.execute(first_pass_result.model_dump())
        return result
    except Exception as e:
        logger.exception("2차 필터링 중 오류 발생")
        raise HTTPException(status_code=500, detail="AI 분석 중 오류가 발생했습니다.")
    
@router.post("/score", response_model=RiskResponse, summary="Step 3. 위험도 점수 계산")
async def calculate_risk_score(
    filter_result: FilterResult = Body(
        ...,
        # [입력 예시] 2차 필터까지 완료된 상태 (모든 적발 내역 포함)
        json_schema_extra={
            "example": {
                "original_text": "야이 개새끼야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라",
                "status": "FILTERED_BY_SECOND_PASS",
                "detected_words": [
                    {"word": "개새끼", "type": "SYSTEM_KEYWORD"},
                    {"word": "니네 집 주소 다 털었다", "type": "AI_AGGRESSION"},
                    {"word": "010-1234-5678", "type": "AI_PRIVACY"}
                ],
                "masked_text": "야이 __F__야 ㅋㅋ __S__ __S__ __S__"
            }
        }
    ),
    risk_scorer: RiskScorer = Depends(get_risk_scorer)
):
    try:
        score = risk_scorer.execute(filter_result.model_dump())
        return {"risk_score": score}
    except Exception as e:
        logger.exception("위험도 계산 중 오류 발생")
        raise HTTPException(status_code=500, detail="위험도 계산 실패")
    
@router.post("/policy", response_model=PolicyResponse, summary="Step 4. 최종 처분 결정")
async def decide_policy(
    user_security_level: int = Body(3, description="유저 보안 레벨 (테스트용)"),
    user_risk_threshold: float = Body(0.65, description="유저 임계값 (테스트용)"),
    data: PolicyRequest = Body(
        ...,
        # [입력 예시] 계산된 점수와 최종 필터링 결과
        json_schema_extra={
            "example": {
                "risk_score": 0.98,
                "filter_result": {
                    "original_text": "야이 개새끼야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라",
                    "status": "FILTERED_BY_SECOND_PASS",
                    "detected_words": [
                        {"word": "개새끼", "type": "SYSTEM_KEYWORD"},
                        {"word": "니네 집 주소 다 털었다", "type": "AI_AGGRESSION"},
                        {"word": "010-1234-5678", "type": "AI_PRIVACY"}
                    ],
                    "masked_text": "야이 __F__야 ㅋㅋ __S__ __S__ __S__"
                }
            }
        }
    ),
    policy_manager: PolicyManager = Depends(get_policy_manager)
):
    try:
        decision = policy_manager.decide_action(
            risk_score=data.risk_score,
            filter_result=data.filter_result.model_dump(),
            user_security_level=user_security_level,
            user_risk_threshold=user_risk_threshold
        )
        return decision
    except Exception as e:
        logger.exception("정책 결정 중 오류 발생")
        raise HTTPException(status_code=500, detail="정책 적용 실패")
    
# --- [YouTube 단순 조회용 API] ---

@router.get("/videos/{video_id}", summary="[DEBUG] 유튜브 영상 메타데이터 조회")
async def get_youtube_video_info(
    video_id: str,
    youtube_service: YoutubeAnalysisService = Depends(get_youtube_analysis_service)
):
    if not youtube_service.youtube:
        raise HTTPException(status_code=503, detail="YouTube API 연결 실패 (API Key 확인 필요)")

    video_info = youtube_service.get_video_details(video_id)
    if not video_info:
        raise HTTPException(status_code=404, detail=f"비디오 ID {video_id}를 찾을 수 없습니다.")

    return video_info

@router.get("/videos/{video_id}/comments", summary="[DEBUG] 유튜브 댓글 수집 (원문)")
async def get_youtube_comments_raw(
    video_id: str, 
    max_pages: int = Query(1, description="수집할 페이지 수"),
    youtube_service: YoutubeAnalysisService = Depends(get_youtube_analysis_service)
):
    if not youtube_service.youtube:
        raise HTTPException(status_code=503, detail="YouTube API 연결 실패 (API Key 확인 필요)")

    comments = youtube_service.get_comments(video_id, max_pages=max_pages)
    return {"video_id": video_id, "total_count": len(comments), "comments": comments}