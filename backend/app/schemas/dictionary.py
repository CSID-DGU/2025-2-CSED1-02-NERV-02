from typing import List, Dict
from pydantic import BaseModel, Field
from enum import Enum

class ListType(str, Enum):
    """사전 타입 (whitelist/blacklist)"""
    whitelist = "whitelist"
    blacklist = "blacklist"

class DictionaryWordsRequest(BaseModel):
    """사전에 단어 추가/삭제 요청"""
    words: List[str] = Field(
        ..., 
        description="추가/삭제할 단어 리스트", 
        json_schema_extra={"example": ["바보", "멍청이"]}
    )

class DictionaryResponse(BaseModel):
    """사용자 사전 조회 응답"""
    whitelist: List[str] = Field(default_factory=list, description="허용 단어 목록")
    blacklist: List[str] = Field(default_factory=list, description="차단 단어 목록")
    total_count: int = Field(..., description="조회된 총 단어 수")

class DictionaryUpdateResponse(BaseModel):
    """사전 업데이트 응답"""
    status: str
    message: str
    processed_count: int
    current_total: Dict[str, int]