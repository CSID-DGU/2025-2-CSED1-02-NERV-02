from fastapi import APIRouter, HTTPException, Body, Depends

from app.schemas.schemas import (
    TextInput, FirstPassResponse, SecondPassResponse, 
    RiskResponse, PolicyInput, PolicyResponse
)

from app.api.deps import (
    get_first_pass_filter, get_second_pass_filter,
    get_risk_scorer, get_policy_manager, get_youtube_client
)

from app.services.first_pass_filter import FirstPassFilter
from app.services.second_pass_filter import SecondPassFilter
from app.services.risk_scorer import RiskScorer
from app.services.policy_manager import PolicyManager
from app.clients.youtube_client import YouTubeClient

router = APIRouter()

# =========================================================
# [API] 개별 모듈 테스트 (Unit APIs)
# =========================================================

@router.post("/first-pass", response_model=FirstPassResponse, summary="Step 1. 1차 필터링")
async def run_first_pass(
    input_data: TextInput,
    first_filter: FirstPassFilter = Depends(get_first_pass_filter)
):
    """
    KoNLPy 및 사전을 이용한 1차 필터링을 수행합니다.
    반환값은 FirstPassResponse 모델을 따릅니다.
    """
    try:
        result = first_filter.execute(input_data.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/second-pass", response_model=SecondPassResponse, summary="Step 2. 2차 필터링 (AI)")
async def run_second_pass(
    first_pass_result: FirstPassResponse = Body(
        ...,
        # [입력 예시] 1차 필터 결과 모델을 그대로 사용 (욕설만 잡힌 상태)
        json_schema_extra={
            "example": {
                "original_text": "야이 개새끼야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라",
                "status": "FILTERED_BY_FIRST_PASS",
                "detected_words": [{"word": "개새끼", "type": "SYSTEM_KEYWORD"}],
                "text_for_filtering": "야이 __F__야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라"
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
        input_dict = first_pass_result.dict()
        result = second_filter.execute(input_dict)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/score", response_model=RiskResponse, summary="Step 3. 위험도 점수 계산")
async def calculate_risk_score(
    filter_result: SecondPassResponse = Body(
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
                "text_for_filtering": "야이 __F__야 ㅋㅋ __S__ __S__ __S__"
            }
        }
    ),
    risk_scorer: RiskScorer = Depends(get_risk_scorer)
):
    try:
        input_dict = filter_result.dict()
        score = risk_scorer.execute(input_dict)
        return {"risk_score": score}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/policy", response_model=PolicyResponse, summary="Step 4. 최종 처분 결정")
async def decide_policy(
    data: PolicyInput = Body(
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
                    "text_for_filtering": "야이 __F__야 ㅋㅋ __S__ __S__ __S__"
                }
            }
        }
    ),
    policy_manager: PolicyManager = Depends(get_policy_manager)
):
    try:
        score = data.risk_score
        f_res = data.filter_result.dict()
        decision = policy_manager.decide_action(score, f_res)
        return decision
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# --- [YouTube 단순 조회용 API] ---

@router.get("/youtube/video", summary="유튜브 영상 메타데이터 조회")
async def get_youtube_video_info(
    video_id: str,
    yt_client: YouTubeClient = Depends(get_youtube_client)
):
    if not yt_client.youtube:
        raise HTTPException(status_code=500, detail="YouTube API 클라이언트가 초기화되지 않았습니다.")
    return yt_client.get_video_details(video_id)

@router.get("/youtube/comments", summary="유튜브 댓글 수집 (원문)")
async def get_youtube_comments_raw(
    video_id: str, 
    max_pages: int = 1,
    yt_client: YouTubeClient = Depends(get_youtube_client)
):
    if not yt_client.youtube:
        raise HTTPException(status_code=500, detail="YouTube API 클라이언트가 초기화되지 않았습니다.")
    comments = yt_client.get_comments(video_id, max_pages=max_pages)
    return {"video_id": video_id, "total_count": len(comments), "comments": comments}