import json
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import VideoAnalysisCache

logger = logging.getLogger(__name__)


class VideoAnalysisCacheRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_valid_cache(
        self,
        *,
        user_id: int,
        video_id: str,
        max_pages: int,
        security_level: int,
        risk_threshold: float,
        enabled_modules: str,
        now: datetime,
    ) -> dict | None:
        stmt = (
            select(VideoAnalysisCache)
            .where(VideoAnalysisCache.user_id == user_id)
            .where(VideoAnalysisCache.video_id == video_id)
            .where(VideoAnalysisCache.max_pages == max_pages)
            .where(VideoAnalysisCache.security_level == security_level)
            .where(VideoAnalysisCache.risk_threshold == risk_threshold)
            .where(VideoAnalysisCache.enabled_modules == enabled_modules)
            .where(VideoAnalysisCache.expires_at > now)
        )
        result = await self.session.execute(stmt)
        cache_row = result.scalar_one_or_none()
        if not cache_row:
            return None

        logger.info(
            "[VideoAnalysisCacheRepository] cache hit user=%s video=%s",
            user_id,
            video_id,
        )
        return json.loads(cache_row.payload_json)

    async def upsert_cache(
        self,
        *,
        user_id: int,
        video_id: str,
        max_pages: int,
        security_level: int,
        risk_threshold: float,
        enabled_modules: str,
        payload: dict,
        analyzed_at: datetime,
        expires_at: datetime,
    ) -> None:
        stmt = (
            select(VideoAnalysisCache)
            .where(VideoAnalysisCache.user_id == user_id)
            .where(VideoAnalysisCache.video_id == video_id)
            .where(VideoAnalysisCache.max_pages == max_pages)
            .where(VideoAnalysisCache.security_level == security_level)
            .where(VideoAnalysisCache.risk_threshold == risk_threshold)
            .where(VideoAnalysisCache.enabled_modules == enabled_modules)
        )
        result = await self.session.execute(stmt)
        cache_row = result.scalar_one_or_none()
        payload_json = json.dumps(payload, ensure_ascii=False)

        if cache_row:
            cache_row.payload_json = payload_json
            cache_row.analyzed_at = analyzed_at
            cache_row.expires_at = expires_at
        else:
            cache_row = VideoAnalysisCache(
                user_id=user_id,
                video_id=video_id,
                max_pages=max_pages,
                security_level=security_level,
                risk_threshold=risk_threshold,
                enabled_modules=enabled_modules,
                payload_json=payload_json,
                analyzed_at=analyzed_at,
                expires_at=expires_at,
            )
            self.session.add(cache_row)

        await self.session.commit()
