import logging

from fastapi import APIRouter, HTTPException, Body, Query, Depends

from collections import Counter

from app.api.deps import (
    get_text_analysis_service,
    get_current_user,
    get_youtube_analysis_service,
    get_keyword_extractor,
)
from app.db.models import User
from app.schemas import (
    TextAnalysisResponse, YoutubeAnalysisResponse, VideoInfo, RawComment,
    KeywordAnalysisResponse, FilteredKeyword, TrendingKeyword,
)
from app.services.filtering.service import TextAnalysisService
from app.services.filtering.keyword_extractor import KeywordExtractor
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
        return await analysis_service.analyze_texts(user=user, texts=[c.text for c in comments])
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
        video_info=VideoInfo(title=video_info["snippet"]["title"], id=video_id),
        total_comments=comment_count,
        results=[RawComment(**c) for c in raw_comments],
    )


@router.post("/keywords", response_model=KeywordAnalysisResponse)
async def analyze_keywords(
    user: User = Depends(get_current_user),
    comments: list[RawComment] = Body(...),
    analysis_service: TextAnalysisService = Depends(get_text_analysis_service),
    extractor: KeywordExtractor = Depends(get_keyword_extractor),
):
    try:
        results = await analysis_service.analyze_texts(user=user, texts=[c.text for c in comments])

        # 필터링된 키워드 빈도 집계
        filtered_counter: Counter[tuple[str, str]] = Counter()
        for r in results:
            for dw in r.details.detected_words:
                filtered_counter[(dw.word, dw.type)] += 1

        filtered_keywords = [
            FilteredKeyword(word=word, count=count, type=wtype)
            for (word, wtype), count in filtered_counter.most_common()
        ]

        # 형태소 분석으로 자주 등장하는 키워드 추출
        texts = [c.text for c in comments]
        trending_raw = extractor.extract(texts)

        # 이미 필터링된 단어는 trending에서 제외
        filtered_words = {fk.word for fk in filtered_keywords}
        trending_keywords = [
            TrendingKeyword(word=kw["word"], count=kw["count"])
            for kw in trending_raw
            if kw["word"] not in filtered_words
        ]

        return KeywordAnalysisResponse(
            filtered_keywords=filtered_keywords,
            trending_keywords=trending_keywords,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"키워드 분석 중 예외 발생 - 유저({user.id})")
        raise HTTPException(status_code=500, detail="서버 내부 오류가 발생했습니다.")
