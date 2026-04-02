import logging

from fastapi import APIRouter, HTTPException, Body, Query, Depends

from app.api.deps import (
    get_text_analysis_service,
    get_current_user,
    get_youtube_analysis_service,
)
from app.db.models import User
from app.schemas import TextAnalysisResponse, YoutubeAnalysisResponse, VideoInfo, RawComment
from app.services.filtering.service import TextAnalysisService
from app.services import YoutubeAnalysisService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/text", response_model=list[TextAnalysisResponse])
async def analyze_comments(
    user: User = Depends(get_current_user),
    comments: list[RawComment] = Body(...),
    analysis_service: TextAnalysisService = Depends(get_text_analysis_service),
):
    try:
        return [
            await analysis_service.analyze_text(user=user, text=comment.text)
            for comment in comments
        ]
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"댓글 분석 중 예외 발생 - 유저({user.id})")
        raise HTTPException(status_code=500, detail="서버 내부 오류가 발생했습니다.")


@router.get("/youtube", response_model=YoutubeAnalysisResponse)
async def get_youtube_data(
    video_id: str = Query(...),
    max_pages: int = Query(default=1, ge=1, le=10),
    user: User = Depends(get_current_user),
    youtube_service: YoutubeAnalysisService = Depends(get_youtube_analysis_service),
):
    video_info = youtube_service.get_video_details(video_id)
    if not video_info:
        raise HTTPException(status_code=404, detail="영상을 찾을 수 없습니다.")

    if user.youtube_channel_id and not youtube_service.verify_channel(video_info, user.youtube_channel_id):
        raise HTTPException(status_code=403, detail="해당 영상은 등록된 채널의 영상이 아닙니다.")

    raw_comments = youtube_service.get_comments(video_id, max_pages=max_pages)

    return YoutubeAnalysisResponse(
        video_info=VideoInfo(title=video_info["snippet"]["title"], id=video_id),
        total_comments=len(raw_comments),
        results=[RawComment(**c) for c in raw_comments],
    )


