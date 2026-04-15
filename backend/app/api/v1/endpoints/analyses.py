import logging

from fastapi import APIRouter, HTTPException, Body, Query, Depends

from app.api.deps import (
    get_text_analysis_service,
    get_current_user,
    get_youtube_analysis_service,
    get_kiwi_engine,
)
from app.db.models import User
from pydantic import BaseModel

from app.schemas import (
    TextAnalysisResponse, YoutubeAnalysisResponse, VideoInfo, RawComment,
    KeywordAnalysisResponse, TrendingKeyword,
)
from app.schemas.enums import KeywordMode
from app.services.filtering.service import TextAnalysisService
from app.services.filtering.context import VideoContext
from app.services.filtering.kiwi_engine import KiwiEngine
from app.services import YoutubeAnalysisService


class AnalyzeTextsRequest(BaseModel):
    comments: list[RawComment]
    video_id: str | None = None
    keyword_modes: dict[str, KeywordMode] = {}


class AnalyzeKeywordsRequest(BaseModel):
    comments: list[RawComment]
    video_id: str | None = None
    keyword_modes: dict[str, KeywordMode] = {}

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/text", response_model=list[TextAnalysisResponse])
async def analyze_comments(
    req: AnalyzeTextsRequest = Body(...),
    user: User = Depends(get_current_user),
    analysis_service: TextAnalysisService = Depends(get_text_analysis_service),
):
    try:
        video_context = VideoContext.from_modes(
            {w: m.value for w, m in req.keyword_modes.items()}
        )
        return await analysis_service.analyze_texts(
            user=user,
            texts=[c.text for c in req.comments],
            video_context=video_context,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"댓글 분석 중 예외 발생 - 유저({user.id})")
        raise HTTPException(status_code=500, detail="서버 내부 오류가 발생했습니다.")


@router.get("/youtube", response_model=YoutubeAnalysisResponse)
async def get_youtube_data(
    video_id: str = Query(...),
    max_pages: int | None = Query(default=None, ge=1, le=50),
    user: User = Depends(get_current_user),
    youtube_service: YoutubeAnalysisService = Depends(get_youtube_analysis_service),
):
    video_info = youtube_service.get_video_details(video_id)
    if not video_info:
        raise HTTPException(status_code=404, detail="영상을 찾을 수 없습니다.")

    if user.youtube_channel_id and not youtube_service.verify_channel(video_info, user.youtube_channel_id):
        raise HTTPException(status_code=403, detail="해당 영상은 등록된 채널의 영상이 아닙니다.")

    comment_count = video_info["statistics"]["commentCount"]
    raw_comments = youtube_service.get_comments(video_id, max_pages=max_pages, comment_count=comment_count)

    return YoutubeAnalysisResponse(
        video_info=VideoInfo(
            title=video_info["snippet"]["title"],
            id=video_id,
            tags=video_info["snippet"].get("tags", []),
            category=video_info["snippet"].get("category"),
            topics=video_info.get("topics", []),
        ),
        # YouTube가 집계한 공식 댓글 수(답글 포함). 실제 수집한 수(len(raw_comments))와는
        # YouTube 내부 상태(삭제·비공개 등)로 인해 차이가 날 수 있어 표시용으로만 사용한다.
        total_comments=comment_count,
        results=[RawComment(**c) for c in raw_comments],
    )


@router.post("/keywords", response_model=KeywordAnalysisResponse)
async def analyze_keywords(
    req: AnalyzeKeywordsRequest = Body(...),
    user: User = Depends(get_current_user),
    kiwi: KiwiEngine = Depends(get_kiwi_engine),
):
    """형태소 분석으로 자주 등장하는 키워드만 추출. filtered_keywords는 프론트에서 /text 결과로부터 직접 집계한다."""
    try:
        texts = [c.text for c in req.comments]
        trending_raw = kiwi.extract_trending(texts)

        trending_keywords = [
            TrendingKeyword(word=kw["word"], count=kw["count"])
            for kw in trending_raw
        ]

        return KeywordAnalysisResponse(
            filtered_keywords=[],
            trending_keywords=trending_keywords,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"키워드 분석 중 예외 발생 - 유저({user.id})")
        raise HTTPException(status_code=500, detail="서버 내부 오류가 발생했습니다.")
