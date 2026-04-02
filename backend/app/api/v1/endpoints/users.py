from fastapi import APIRouter, Body, Depends, HTTPException

from app.db.models import User
from app.schemas import (
    ListType,
    DictionaryWordsRequest, DictionaryResponse, DictionaryUpdateResponse,
    UserSettingsResponse, UserSettingsUpdate
)

from app.api.deps import get_dictionary_service, get_user_service, get_current_user, get_youtube_analysis_service

from app.services.dictionary_service import DictionaryService
from app.services.user_service import UserService
from app.services.youtube_analysis_service import YoutubeAnalysisService

router = APIRouter()

# =========================================================
# [API] 시스템 설정 관리 API (System Config APIs)
# =========================================================

@router.get("/dictionaries", response_model=DictionaryResponse, summary="사용자 사전 전체 조회")
async def get_user_dictionaries(
    user: User = Depends(get_current_user),
    dict_service: DictionaryService = Depends(get_dictionary_service)
):
    """
    사용자의 whitelist와 blacklist를 한 번에 조회합니다.
    """

    data = await dict_service.get_user_dictionaries(user.id)
    
    whitelist = data.get('whitelist', [])
    blacklist = data.get('blacklist', [])
    
    return DictionaryResponse(
        whitelist=whitelist,
        blacklist=blacklist,
        total_count=len(whitelist) + len(blacklist)
    )

@router.post("/dictionaries/{list_type}", response_model=DictionaryUpdateResponse, summary="사전에 단어 추가")
async def add_dictionary_words(
    list_type: ListType,
    req: DictionaryWordsRequest,
    user: User = Depends(get_current_user),
    dict_service: DictionaryService = Depends(get_dictionary_service)
):
    """
    사용자 사전(whitelist 또는 blacklist)에 단어를 일괄 추가합니다.
    """
    
    added_count = await dict_service.add_user_words(
        user_id=user.id,
        words=req.words,
        list_type=list_type
    )
    
    data = await dict_service.get_user_dictionaries(user.id)

    return DictionaryUpdateResponse(
        status="success",
        message=f"{added_count}개의 단어가 {list_type}에 추가되었습니다.",
        processed_count=added_count,
        current_total={
            "whitelist": len(data['whitelist']),
            "blacklist": len(data['blacklist'])
        }
    )

@router.delete("/dictionaries/{list_type}", response_model=DictionaryUpdateResponse, summary="단어 일괄 삭제")
async def remove_dictionary_words(
    list_type: ListType,
    req: DictionaryWordsRequest,
    user: User = Depends(get_current_user),
    dict_service: DictionaryService = Depends(get_dictionary_service)
):
    """
    사용자 사전에서 단어를 일괄 삭제합니다.
    """
    
    removed_count = await dict_service.remove_user_words(
        user_id=user.id,
        words=req.words,
        list_type=list_type
    )

    data = await dict_service.get_user_dictionaries(user.id)

    return DictionaryUpdateResponse(
        status="success",
        message=f"{removed_count}개의 단어가 사전에서 삭제되었습니다.",
        processed_count=removed_count,
        current_total={
            "whitelist": len(data['whitelist']),
            "blacklist": len(data['blacklist'])
        }
    )

@router.get("/settings", response_model=UserSettingsResponse, summary="유저 개인 설정 조회")
async def get_user_settings(
    user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """사용자 필터링 설정을 조회합니다."""
    user = await user_service.get_settings(user.id)
    
    return {
        "user_id": user.id,
        "security_level": user.security_level,
        "risk_threshold": user.risk_threshold,
        "use_detail_ai_model": user.use_detail_ai_model,
        "enabled_modules": user.enabled_modules,
        "youtube_channel_id": user.youtube_channel_id,
        "youtube_channel_name": user.youtube_channel_name,
        "youtube_channel_url": user.youtube_channel_url,
        "youtube_thumbnail_url": user.youtube_thumbnail_url,
    }

@router.patch("/settings", response_model=UserSettingsResponse,summary="유저 개인 필터링 설정 변경")
async def update_user_settings(
    req: UserSettingsUpdate,
    user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """사용자 필터링 설정을 부분 업데이트합니다 (PATCH)."""
    user = await user_service.update_settings(user.id, req.model_dump(exclude_unset=True))

    return {
        "user_id": user.id,
        "security_level": user.security_level,
        "risk_threshold": user.risk_threshold,
        "use_detail_ai_model": user.use_detail_ai_model,
        "enabled_modules": user.enabled_modules,
        "youtube_channel_id": user.youtube_channel_id,
        "youtube_channel_name": user.youtube_channel_name,
        "youtube_channel_url": user.youtube_channel_url,
        "youtube_thumbnail_url": user.youtube_thumbnail_url,
    }


@router.put("/youtube-channel", summary="YouTube 채널 연동")
async def link_youtube_channel(
    channel_id: str = Body(..., embed=True),
    user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    youtube_service: YoutubeAnalysisService = Depends(get_youtube_analysis_service),
):
    """YouTube 채널 ID를 검증하고 사용자 계정에 연동합니다."""
    channel_info = youtube_service.get_channel_info(channel_id)
    if not channel_info:
        raise HTTPException(status_code=404, detail="유효하지 않은 채널 ID입니다.")

    await user_service.update_settings(user.id, {
        "youtube_channel_id": channel_info["channel_id"],
        "youtube_channel_name": channel_info["channel_name"],
        "youtube_channel_url": channel_info["channel_url"],
        "youtube_thumbnail_url": channel_info["thumbnail_url"],
    })

    return channel_info


@router.delete("/youtube-channel", summary="YouTube 채널 연동 해제")
async def unlink_youtube_channel(
    user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    """사용자 계정에서 YouTube 채널 연동을 해제합니다."""
    await user_service.update_settings(user.id, {
        "youtube_channel_id": None,
        "youtube_channel_name": None,
        "youtube_channel_url": None,
        "youtube_thumbnail_url": None,
    })

    return {"status": "success", "message": "채널 연동이 해제되었습니다."}