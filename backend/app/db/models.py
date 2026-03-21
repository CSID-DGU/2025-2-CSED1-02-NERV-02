from datetime import datetime
from sqlalchemy import String, ForeignKey, UniqueConstraint, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    
    security_level: Mapped[int] = mapped_column(default=3)           
    risk_threshold: Mapped[float] = mapped_column(default=0.65)          

    # 2차 필터링 개발 방향에 따라 삭제 가능성 있음
    use_detail_ai_model: Mapped[bool] = mapped_column(Boolean, default=False)
    basic_threshold: Mapped[float] = mapped_column(Float, default=0.9)
    enabled_modules: Mapped[str] = mapped_column(String(255), default="ALL")

    youtube_channel_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    youtube_channel_name: Mapped[str | None] = mapped_column(String(100))            
    youtube_channel_url: Mapped[str | None] = mapped_column(String(255))             
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


class SystemDictionary(Base):
    __tablename__ = "system_dictionaries"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(50), default="SYSTEM_KEYWORD") 
    created_at: Mapped[datetime] = mapped_column(default=func.now())