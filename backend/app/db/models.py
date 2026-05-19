from datetime import datetime
from sqlalchemy import String, ForeignKey, UniqueConstraint, Boolean, Integer, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    
    security_level: Mapped[str] = mapped_column(String(10), default="MEDIUM")

    ai_soften_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    use_detail_ai_model: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled_modules: Mapped[str] = mapped_column(String(255), default="spam,pii,politics,criticism,basic,sexual")

    youtube_channel_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    youtube_channel_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    youtube_channel_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    youtube_thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)             
    is_active: Mapped[bool] = mapped_column(default=True)                            

    created_at: Mapped[datetime] = mapped_column(default=func.now())

    dictionaries: Mapped[list["UserDictionary"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class UserDictionary(Base):
    __tablename__ = "user_dictionaries"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    
    word: Mapped[str] = mapped_column(String(100), index=True)
    list_type: Mapped[str] = mapped_column(String(20)) # 'WHITELIST' 또는 'BLACKLIST'
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    
    user: Mapped["User"] = relationship(back_populates="dictionaries")

    __table_args__ = (
        UniqueConstraint('user_id', 'word', name='uq_user_word'),
    )


class VideoAnalysisCache(Base):
    __tablename__ = "video_analysis_cache"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    video_id: Mapped[str] = mapped_column(String(32), index=True)
    max_pages: Mapped[int] = mapped_column(Integer, default=1)
    security_level: Mapped[str] = mapped_column(String(10))
    ai_soften_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled_modules: Mapped[str] = mapped_column(String(255), default="spam,pii,politics,criticism,basic,sexual")
    payload_json: Mapped[str] = mapped_column(Text)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "video_id",
            "max_pages",
            "security_level",
            "ai_soften_enabled",
            "enabled_modules",
            name="uq_video_analysis_cache_key",
        ),
    )


class CommentAnalysisCache(Base):
    __tablename__ = "comment_analysis_cache"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    video_id: Mapped[str] = mapped_column(String(32), index=True)
    comment_id: Mapped[str] = mapped_column(String(128), index=True)
    security_level: Mapped[str] = mapped_column(String(10))
    ai_soften_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled_modules: Mapped[str] = mapped_column(String(255), default="spam,pii,politics,criticism,basic,sexual")
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "video_id",
            "comment_id",
            "security_level",
            "ai_soften_enabled",
            "enabled_modules",
            name="uq_comment_analysis_cache_key",
        ),
    )
