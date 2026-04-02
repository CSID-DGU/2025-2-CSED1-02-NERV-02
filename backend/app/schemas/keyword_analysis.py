from pydantic import BaseModel, Field


class FilteredKeyword(BaseModel):
    word: str = Field(..., description="필터링된 키워드")
    count: int = Field(..., description="등장 횟수")
    type: str = Field(..., description="사전 유형 (SYSTEM_KEYWORD, USER_BLACKLIST)")


class TrendingKeyword(BaseModel):
    word: str = Field(..., description="자주 등장하는 키워드")
    count: int = Field(..., description="등장 횟수")


class KeywordAnalysisResponse(BaseModel):
    filtered_keywords: list[FilteredKeyword] = Field(default_factory=list)
    trending_keywords: list[TrendingKeyword] = Field(default_factory=list)
