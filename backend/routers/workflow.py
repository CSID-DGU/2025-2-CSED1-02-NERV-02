from fastapi import APIRouter, HTTPException, Body, Depends
from schemas import TextInput, AnalysisResult, YoutubeAnalysisResponse

from dependencies import (
    get_first_pass_filter,
    get_second_pass_filter,
    get_risk_scorer,
    get_policy_manager,
    get_youtube_client
)

from filter_api.core.first_pass_filter import FirstPassFilter
from filter_api.core.second_pass_filter import SecondPassFilter
from filter_api.core.risk_scorer import RiskScorer
from filter_api.core.policy_manager import PolicyManager
from filter_api.clients.youtube_client import YouTubeClient

router = APIRouter(
    prefix="/api/workflow",
    tags=["Integrative Workflow (Full Process)"],
)

# =========================================================
# 내부 헬퍼 함수 (파이프라인 실행)
# =========================================================

def _run_pipeline(
    text: str,
    first_filter: FirstPassFilter,
    second_filter: SecondPassFilter,
    risk_scorer: RiskScorer,
    policy_manager: PolicyManager
) -> dict:
    """모든 필터링 단계를 거쳐 최종 결과를 반환하는 핵심 비즈니스 로직입니다."""
    res = first_filter.execute(text)
    res = second_filter.execute(res)
    score = risk_scorer.execute(res)
    final_decision = policy_manager.decide_action(score, res)
    
    return {
        "original_text": res['original_text'],
        "processed_text": final_decision['processed_text'],
        "action": final_decision['action'],
        "score": score,
        "details": res
    }

# =========================================================
# [API] 전체 통합 워크플로우 (Workflow APIs)
# =========================================================

@router.post("/analyze-text", response_model=AnalysisResult, summary="단일 텍스트 전체 분석")
async def analyze_single_text(
    input_data: TextInput = Body(
        ...,
        json_schema_extra={
            "example": {"text": "야이 개새끼야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라"}
        }
    ),
    first_filter: FirstPassFilter = Depends(get_first_pass_filter),
    second_filter: SecondPassFilter = Depends(get_second_pass_filter),
    risk_scorer: RiskScorer = Depends(get_risk_scorer),
    policy_manager: PolicyManager = Depends(get_policy_manager)
):
    try:
        result = _run_pipeline(input_data.text, first_filter, second_filter, risk_scorer, policy_manager)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze-youtube", response_model=YoutubeAnalysisResponse, summary="유튜브 영상 댓글 분석")
async def analyze_youtube_video(
    video_id: str, 
    max_pages: int = 1,
    first_filter: FirstPassFilter = Depends(get_first_pass_filter),
    second_filter: SecondPassFilter = Depends(get_second_pass_filter),
    risk_scorer: RiskScorer = Depends(get_risk_scorer),
    policy_manager: PolicyManager = Depends(get_policy_manager),
    yt_client: YouTubeClient = Depends(get_youtube_client)
):
    if not yt_client.youtube:
        raise HTTPException(status_code=500, detail="YouTube API 연결 실패 (API Key 확인 필요)")
    
    video_info = yt_client.get_video_details(video_id)
    comments = yt_client.get_comments(video_id, max_pages=max_pages)
    
    analyzed_results = []
    blocked_count = 0
    
    for comm in comments:
        text = comm['text_original']
        # 내부 파이프라인 함수 호출
        analysis = _run_pipeline(text, first_filter, second_filter, risk_scorer, policy_manager)
        
        summary = {
            "author": comm['author_display_name'],
            "published_at": comm['published_at'],
            "original": text,
            "processed": analysis['processed_text'],
            "action": analysis['action'],
            "risk_score": analysis['score'],
            "violation_tags": [item['type'] for item in analysis['details']['detected_words']]
        }
        analyzed_results.append(summary)
        
        if analysis['action'] != "PASS":
            blocked_count += 1

    video_title = "Unknown Video"
    if video_info and isinstance(video_info, dict):
        video_title = video_info.get('snippet', {}).get('title', 'Unknown Video')

    return {
        "video_info": {"title": video_title, "id": video_id},
        "stats": {
            "total_comments": len(comments), 
            "blocked_comments": blocked_count, 
            "clean_comments": len(comments) - blocked_count
        },
        "results": analyzed_results
    }