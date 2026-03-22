import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CommentAnalysisCache


class CommentAnalysisCacheRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_many(
        self,
        *,
        user_id: int,
        video_id: str,
        comment_ids: list[str],
        security_level: int,
        risk_threshold: float,
        enabled_modules: str,
    ) -> dict[str, dict]:
        if not comment_ids:
            return {}

        stmt = (
            select(CommentAnalysisCache)
            .where(CommentAnalysisCache.user_id == user_id)
            .where(CommentAnalysisCache.video_id == video_id)
            .where(CommentAnalysisCache.comment_id.in_(comment_ids))
            .where(CommentAnalysisCache.security_level == security_level)
            .where(CommentAnalysisCache.risk_threshold == risk_threshold)
            .where(CommentAnalysisCache.enabled_modules == enabled_modules)
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return {row.comment_id: json.loads(row.payload_json) for row in rows}

    async def upsert_many(
        self,
        *,
        user_id: int,
        video_id: str,
        entries: list[dict],
        security_level: int,
        risk_threshold: float,
        enabled_modules: str,
        seen_at: datetime,
    ) -> None:
        if not entries:
            return

        comment_ids = [entry["comment_id"] for entry in entries]
        stmt = (
            select(CommentAnalysisCache)
            .where(CommentAnalysisCache.user_id == user_id)
            .where(CommentAnalysisCache.video_id == video_id)
            .where(CommentAnalysisCache.comment_id.in_(comment_ids))
            .where(CommentAnalysisCache.security_level == security_level)
            .where(CommentAnalysisCache.risk_threshold == risk_threshold)
            .where(CommentAnalysisCache.enabled_modules == enabled_modules)
        )
        result = await self.session.execute(stmt)
        existing_rows = {
            row.comment_id: row
            for row in result.scalars().all()
        }

        for entry in entries:
            payload_json = json.dumps(entry["payload"], ensure_ascii=False)
            existing_row = existing_rows.get(entry["comment_id"])
            if existing_row:
                existing_row.payload_json = payload_json
                existing_row.last_seen_at = seen_at
                continue

            self.session.add(
                CommentAnalysisCache(
                    user_id=user_id,
                    video_id=video_id,
                    comment_id=entry["comment_id"],
                    security_level=security_level,
                    risk_threshold=risk_threshold,
                    enabled_modules=enabled_modules,
                    payload_json=payload_json,
                    created_at=seen_at,
                    last_seen_at=seen_at,
                )
            )

        await self.session.commit()
