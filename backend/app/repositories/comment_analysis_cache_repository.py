import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.mysql import insert
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

        rows = [
            {
                "user_id": user_id,
                "video_id": video_id,
                "comment_id": entry["comment_id"],
                "security_level": security_level,
                "risk_threshold": risk_threshold,
                "enabled_modules": enabled_modules,
                "payload_json": json.dumps(entry["payload"], ensure_ascii=False),
                "created_at": seen_at,
                "last_seen_at": seen_at,
            }
            for entry in entries
        ]

        stmt = insert(CommentAnalysisCache).values(rows)
        stmt = stmt.on_duplicate_key_update(
            payload_json=stmt.inserted.payload_json,
            last_seen_at=stmt.inserted.last_seen_at,
        )
        await self.session.execute(stmt)
        await self.session.commit()
