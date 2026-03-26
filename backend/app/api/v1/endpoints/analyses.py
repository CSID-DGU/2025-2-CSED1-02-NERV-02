from datetime import datetime, timedelta, timezone
import logging

from fastapi import APIRouter, HTTPException, Body, Depends

from app.api.deps import (
    get_comment_analysis_cache_repository,
    get_comment_filtering_service,
    get_user_repository,
    get_video_analysis_cache_repository,
    get_youtube_client,
    get_current_user
)
from app.clients.youtube_client import YouTubeClient
from app.core import settings
from app.repositories.comment_analysis_cache_repository import CommentAnalysisCacheRepository
from app.repositories.user import UserRepository
from app.repositories.video_analysis_cache_repository import VideoAnalysisCacheRepository
from app.schemas import TextAnalysisRequest, AnalysisResult, YoutubeAnalysisResponse, YoutubeAnalysisRequest
from app.services.comment_filtering_service import CommentFilteringService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/text", response_model=AnalysisResult, summary="?â‘¥ì”ª ?ë¿ë’ª???ê¾©ê»œ éºê¾©ê½")
async def analyze_single_text(
    user_id: int = Depends(get_current_user),
    input_data: TextAnalysisRequest = Body(
        ...,
        json_schema_extra={
            "example": {"text": "?ì‡±ì”  åª›ì’–ê¹‰?ì‡±ë¹ž ?ë—£ë€‘ ?ëˆê½• ï§ž?äºŒì‡±ëƒ¼ ???ëª„ë¿€??010-1234-5678 è«›ã…ºë§Œ è­°ê³—ë––?ëŒ€ì”ª"}
        },
    ),
    filtering_service: CommentFilteringService = Depends(get_comment_filtering_service),
):
    try:
        analysis = await filtering_service.process_comment(
            user_id=user_id,
            comment_text=input_data.text,
        )
        if analysis.get("action") == "ERROR":
            reason = analysis.get("reason", "Unknown Error")
            if reason == "USER_NOT_FOUND":
                raise HTTPException(status_code=404, detail=f"?ì¢Ž? ID {user_id}ç‘œ?ï§¡ì– ì“£ ???ë†ë’¿?ëˆë–Ž.")

            logger.error(f"?ì’•í‰¬???ëŒ€? ?ã…»ìªŸ: {reason}")
            raise HTTPException(status_code=500, detail="?ì’•ì¾­ ?ëŒ€? ?ã…»ìªŸåª›Â€ è«›ì’–ê¹®?ë‰ë’¿?ëˆë–Ž.")

        return {
            "original_text": input_data.text,
            "processed_text": analysis["processed_text"],
            "action": analysis["action"],
            "score": analysis["score"],
            "details": analysis["details"],
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"?ë¿ë’ª??éºê¾©ê½ ä»¥??ë‰ê¸½ç§»?ï§ì‚µë¸³ ?ã…»ìªŸ è«›ì’–ê¹® - ?ì¢Ž?({user_id})")
        raise HTTPException(status_code=500, detail="?ì’•ì¾­ ?ëŒ€? ?ã…»ìªŸåª›Â€ è«›ì’–ê¹®?ë‰ë’¿?ëˆë–Ž.")


@router.post("/youtube", response_model=YoutubeAnalysisResponse, summary="?ì¢ë’ é‡‰??ê³¸ê¸½ ?ë³¤? éºê¾©ê½")
async def analyze_youtube_video(
    user_id: int = Depends(get_current_user),
    req: YoutubeAnalysisRequest = Body(...),
    filtering_service: CommentFilteringService = Depends(get_comment_filtering_service),
    yt_client: YouTubeClient = Depends(get_youtube_client),
    user_repo: UserRepository = Depends(get_user_repository),
    cache_repo: VideoAnalysisCacheRepository = Depends(get_video_analysis_cache_repository),
    comment_cache_repo: CommentAnalysisCacheRepository = Depends(get_comment_analysis_cache_repository),
):
    user = await user_repo.get_user_settings(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"?ì¢Ž? ID {user_id}ç‘œ?ï§¡ì– ì“£ ???ë†ë’¿?ëˆë–Ž.")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cached_response = await cache_repo.get_valid_cache(
        user_id=user_id,
        video_id=req.video_id,
        max_pages=req.max_pages,
        security_level=user.security_level,
        risk_threshold=user.risk_threshold,
        enabled_modules=user.enabled_modules,
        now=now,
    )
    if cached_response:
        return cached_response

    if not yt_client.youtube:
        raise HTTPException(status_code=503, detail="YouTube API ?ê³Œê» ?ã…½ë™£ (API Key ?ëº¤ì”¤ ?ê¾©ìŠ‚)")

    video_info = yt_client.get_video_details(video_id=req.video_id)
    if not video_info:
        raise HTTPException(status_code=404, detail=f"é®ê¾¨ëµ’??ID {req.video_id}ç‘œ?ï§¡ì– ì“£ ???ë†ë’¿?ëˆë–Ž.")

    comments = yt_client.get_comments(req.video_id, max_pages=req.max_pages)
    cached_comment_summaries = await comment_cache_repo.get_many(
        user_id=user_id,
        video_id=req.video_id,
        comment_ids=[comment["comment_id"] for comment in comments],
        security_level=user.security_level,
        risk_threshold=user.risk_threshold,
        enabled_modules=user.enabled_modules,
    )

    analyzed_results = []
    blocked_count = 0
    comment_cache_entries = []

    for comm in comments:
        comment_id = comm["comment_id"]
        cached_summary = cached_comment_summaries.get(comment_id)
        if cached_summary:
            analyzed_results.append(cached_summary)
            if cached_summary["action"] != "PASS":
                blocked_count += 1
            comment_cache_entries.append({
                "comment_id": comment_id,
                "payload": cached_summary,
            })
            continue

        text = comm["text_original"]
        analysis = await filtering_service.process_comment(user_id=user_id, comment_text=text)

        if analysis.get("action") == "ERROR":
            logger.warning(f"?ë³¤? éºê¾©ê½ ?ã…½ë™£ - ?ë¬’ê½¦?? {comm['author_display_name']}")
            continue

        summary = {
            "author": comm["author_display_name"],
            "published_at": comm["published_at"],
            "original": text,
            "processed": analysis["processed_text"],
            "action": analysis["action"],
            "risk_score": analysis["score"],
            "violation_tags": [item["type"] for item in analysis["details"]["detected_words"]],
        }
        analyzed_results.append(summary)
        comment_cache_entries.append({
            "comment_id": comment_id,
            "payload": summary,
        })

        if analysis["action"] != "PASS":
            blocked_count += 1

    video_title = "Unknown Video"
    if isinstance(video_info, dict):
        video_title = video_info.get("snippet", {}).get("title", "Unknown Video")

    response_payload = {
        "video_info": {"title": video_title, "id": req.video_id},
        "stats": {
            "total_comments": len(comments),
            "blocked_comments": blocked_count,
            "clean_comments": len(comments) - blocked_count,
        },
        "results": analyzed_results,
    }

    await comment_cache_repo.upsert_many(
        user_id=user_id,
        video_id=req.video_id,
        entries=comment_cache_entries,
        security_level=user.security_level,
        risk_threshold=user.risk_threshold,
        enabled_modules=user.enabled_modules,
        seen_at=now,
    )

    await cache_repo.upsert_cache(
        user_id=user_id,
        video_id=req.video_id,
        max_pages=req.max_pages,
        security_level=user.security_level,
        risk_threshold=user.risk_threshold,
        enabled_modules=user.enabled_modules,
        payload=response_payload,
        analyzed_at=now,
        expires_at=now + timedelta(seconds=settings.VIDEO_ANALYSIS_CACHE_TTL_SECONDS),
    )

    return response_payload
