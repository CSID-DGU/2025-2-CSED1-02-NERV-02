from fastapi import APIRouter, HTTPException, Query, Depends
from dotenv import set_key, find_dotenv

from app.core import settings
from app.schemas import (
    ListType,
    DictionaryWordsRequest, DictionaryResponse, DictionaryUpdateResponse,
    UserSettingsResponse, UserSettingsUpdate
)

from app.api.deps import get_dictionary_service, get_first_pass_filter, get_user_repository, get_current_user

from app.services.dictionary_service import DictionaryService, ListType
from app.engines.first_pass_filter import FirstPassFilter
from app.repositories.user import UserRepository

router = APIRouter()

# =========================================================
# [API] 시스템 설정 관리 API (System Config APIs)
# =========================================================

@router.get("/dictionaries", response_model=DictionaryResponse, summary="사용자 사전 전체 조회")
async def get_user_dictionaries(
    user_id: int = Depends(get_current_user),
    dict_service: DictionaryService = Depends(get_dictionary_service)
):
    """
    사용자의 whitelist와 blacklist를 한 번에 조회합니다.
    """

    data = await dict_service.get_user_dictionaries(user_id)
    
    whitelist = data.get('whitelist', [])
    blacklist = data.get('blacklist', [])
    
    return {
        "whitelist": whitelist,
        "blacklist": blacklist,
        "total_count": len(whitelist) + len(blacklist)
    }

@router.post("/dictionaries/{list_type}", response_model=DictionaryUpdateResponse, summary="사전에 단어 추가")
async def add_dictionary_words(
    list_type: ListType,
    req: DictionaryWordsRequest,
    user_id: int = Depends(get_current_user),
    dict_service: DictionaryService = Depends(get_dictionary_service),
    first_filter: FirstPassFilter = Depends(get_first_pass_filter)
):
    """
    사용자 사전(whitelist 또는 blacklist)에 단어를 일괄 추가합니다.
    """
    
    added_count = await dict_service.add_user_words(
        user_id=user_id,
        words=req.words,
        list_type=ListType(list_type.value)
    )
    
    if added_count > 0:
        await first_filter.reload_engine(user_id)
    
    data = await dict_service.get_user_dictionaries(user_id)

    return {
        "status": "success",
        "message": f"{added_count}개의 단어가 {list_type}에 추가되었습니다.",
        "processed_count": added_count,
        "current_total": {
            "whitelist": len(data['whitelist']),
            "blacklist": len(data['blacklist'])
        }
    }

@router.delete("/dictionaries/{list_type}", response_model=DictionaryUpdateResponse, summary="단어 일괄 삭제")
async def remove_dictionary_words(
    list_type: ListType,
    req: DictionaryWordsRequest,
    user_id: int = Depends(get_current_user),
    dict_service: DictionaryService = Depends(get_dictionary_service),
    first_filter: FirstPassFilter = Depends(get_first_pass_filter)
):
    """
    사용자 사전에서 단어를 일괄 삭제합니다.
    """
    
    removed_count = await dict_service.remove_user_words(
        user_id=user_id,
        words=req.words
    )
    
    if removed_count > 0:
        await first_filter.reload_engine(user_id)

    data = await dict_service.get_user_dictionaries(user_id)

    return {
        "status": "success",
        "message": f"{removed_count}개의 단어가 사전에서 삭제되었습니다.",
        "processed_count": removed_count,
        "current_total": {
            "whitelist": len(data['whitelist']),
            "blacklist": len(data['blacklist'])
        }
    }

@router.get("/settings", response_model=UserSettingsResponse, summary="유저 개인 설정 조회")
async def get_user_settings(
    user_id: int = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """사용자 필터링 설정을 조회합니다."""
    user = await user_repo.get_user_settings(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"유저 ID {user_id}를 찾을 수 없습니다.")
    
    return {
        "user_id": user.id,
        "security_level": user.security_level,
        "risk_threshold": user.risk_threshold,
        "use_detail_ai_model": user.use_detail_ai_model,
        "basic_threshold": user.basic_threshold,
        "enabled_modules": user.enabled_modules
    }

@router.patch("/settings", summary="유저 개인 필터링 설정 변경")
async def update_user_settings(
    req: UserSettingsUpdate,
    user_id: int = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """사용자 필터링 설정을 부분 업데이트합니다 (PATCH)."""
    user = await user_repo.get_user_settings(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"유저 ID {user_id}를 찾을 수 없습니다.")
    
    # 전달받은 값이 있을 때만 DB 엔티티 수정
    if req.security_level is not None: user.security_level = req.security_level
    if req.risk_threshold is not None: user.risk_threshold = req.risk_threshold
    if req.use_detail_ai_model is not None: user.use_detail_ai_model = req.use_detail_ai_model
    if req.basic_threshold is not None: user.basic_threshold = req.basic_threshold
    if req.enabled_modules is not None: user.enabled_modules = req.enabled_modules
    
    await user_repo.session.commit()
    
    return {
        "status": "success",
        "message": f"유저({user_id}) 설정이 업데이트되었습니다."
    }