from fastapi import APIRouter, HTTPException, Body, Depends, Query
import logging

from app.schemas import TextInput, AnalysisResult, YoutubeAnalysisResponse, YoutubeAnalysisRequest
from app.api.deps import get_comment_filtering_service, get_youtube_client
from app.services.comment_filtering_service import CommentFilteringService
from app.clients.youtube_client import YouTubeClient

router = APIRouter()
logger = logging.getLogger(__name__)

# =========================================================
# [API] 전체 통합 워크플로우 (Workflow APIs)
# =========================================================

@router.post("/users/{user_id}/text-analyses", response_model=AnalysisResult, summary="단일 텍스트 전체 분석")
async def analyze_single_text(
    user_id: int,
    input_data: TextInput = Body(
        ...,
        json_schema_extra={
            "example": {"text": "야이 개새끼야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라"}
        }
    ),
    filtering_service: CommentFilteringService = Depends(get_comment_filtering_service)
):
    try:
        analysis = await filtering_service.process_comment(
            user_id=user_id,
            comment_text=input_data.text
        )
        if analysis.get("action") == "ERROR":
            reason = analysis.get("reason", "Unknown Error")
            if reason == "USER_NOT_FOUND":
                raise HTTPException(status_code=404, detail=f"유저 ID {user_id}를 찾을 수 없습니다.")
            else:
                logger.error(f"서비스 내부 오류: {reason}")
                raise HTTPException(status_code=500, detail="서버 내부 오류가 발생했습니다.")
        
        return {
            "original_text": input_data.text,
            "processed_text": analysis['processed_text'],
            "action": analysis['action'],
            "score": analysis['score'],
            "details": analysis['details']
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"텍스트 분석 중 예상치 못한 오류 발생 - 유저({user_id})")
        raise HTTPException(status_code=500, detail="서버 내부 오류가 발생했습니다.")

@router.post("/users/{user_id}/youtube-analyses", response_model=YoutubeAnalysisResponse, summary="유튜브 영상 댓글 분석")
async def analyze_youtube_video(
    user_id: int,
    req: YoutubeAnalysisRequest = Body(...),
    filtering_service: CommentFilteringService = Depends(get_comment_filtering_service),
    yt_client: YouTubeClient = Depends(get_youtube_client)
):
    if not yt_client.youtube:
        raise HTTPException(status_code=503, detail="YouTube API 연결 실패 (API Key 확인 필요)")
    
    video_info = yt_client.get_video_details(video_id=req.video_id)
    if not video_info:
        raise HTTPException(status_code=404, detail=f"비디오 ID {req.video_id}를 찾을 수 없습니다.")

    comments = yt_client.get_comments(req.video_id, max_pages=req.max_pages)
    
    analyzed_results = []
    blocked_count = 0
    
    for comm in comments:
        text = comm['text_original']
        analysis = await filtering_service.process_comment(user_id=user_id, comment_text=text)
        
        if analysis.get("action") == "ERROR":
            logger.warning(f"댓글 분석 실패 - 작성자: {comm['author_display_name']}")
            continue

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
        "video_info": {"title": video_title, "id": req.video_id},
        "stats": {
            "total_comments": len(comments), 
            "blocked_comments": blocked_count, 
            "clean_comments": len(comments) - blocked_count
        },
        "results": analyzed_results
    }