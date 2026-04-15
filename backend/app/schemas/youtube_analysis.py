from pydantic import BaseModel, Field
from datetime import datetime
from app.schemas.enums import WordType, ModerationAction

class VideoInfo(BaseModel):
    title: str
    id: str
    tags: list[str] = []
    category: str | None = None
    topics: list[str] = []

class YoutubeAnalysisRequest(BaseModel):
    """유튜브 영상 분석 요청"""
    video_id: str
    max_pages: int = Field(default=1, ge=1, le=10)

class RawComment(BaseModel):
    comment_id: str
    text: str
    author: str
    published_at: datetime
    parent_id: str | None = None

class YoutubeAnalysisResponse(BaseModel):
    """유튜브 영상 분석 응답"""
    video_info: VideoInfo
    total_comments: int
    results: list[RawComment]