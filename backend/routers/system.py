from fastapi import APIRouter, HTTPException, Query, Depends
from dotenv import set_key, find_dotenv

from config import config
from schemas import(
    DictionaryRequest,
    DictionaryResponse,
    DictionaryUpdateResponse,
    SystemConfigResponse,
    SystemConfigUpdate
)

from dependencies import get_first_pass_filter

from filter_api.core.first_pass_filter import FirstPassFilter

router = APIRouter(
    prefix="/api/system",
    tags=["System & Config"],
    responses={404: {"description": "Not found"}},
)

# =========================================================
# [API] 시스템 설정 관리 API (System Config APIs)
# =========================================================

@router.get("/dictionary", response_model=DictionaryResponse, summary="사용자 사전 목록 조회")
async def get_dictionary_list(
    list_type: str = Query(..., description="조회할 타입 ('whitelist' 또는 'blacklist')"),
    first_filter: FirstPassFilter = Depends(get_first_pass_filter)
):
    """
    사용자 사전 목록을 조회합니다. list_type('whitelist', 'blacklist')을 지정해야 합니다.
    """
    if list_type not in ['whitelist', 'blacklist']:
        raise HTTPException(status_code=400, detail="list_type은 'whitelist' 또는 'blacklist'여야 합니다.")

    data = first_filter.get_user_dictionary(list_type)
    
    whitelist = data.get('whitelist', []) if data else []
    blacklist = data.get('blacklist', []) if data else []
    
    return {
        "whitelist": whitelist,
        "blacklist": blacklist,
        "total_count": len(whitelist) + len(blacklist)
    }

@router.post("/dictionary", response_model=DictionaryUpdateResponse, summary="단어 일괄 추가")
async def add_dictionary_words(
    req: DictionaryRequest,
    first_filter: FirstPassFilter = Depends(get_first_pass_filter)
):
    """
    여러 단어를 리스트로 받아 사전에 추가합니다. (중복 무시)
    """
    if req.list_type not in ['whitelist', 'blacklist']:
        raise HTTPException(status_code=400, detail="list_type 오류")
    
    added_count = first_filter._update_user_dictionary(req.words, req.list_type, action='add')
    
    return {
        "status": "success",
        "message": f"{added_count}개의 단어가 {req.list_type}에 추가되었습니다.",
        "processed_count": added_count,
        "current_total": {
            "whitelist": len(first_filter.user_whitelist),
            "blacklist": len(first_filter.user_blacklist)
        }
    }

@router.delete("/dictionary", response_model=DictionaryUpdateResponse, summary="단어 일괄 삭제")
async def remove_dictionary_words(
    req: DictionaryRequest,
    first_filter: FirstPassFilter = Depends(get_first_pass_filter)
):
    """
    여러 단어를 리스트로 받아 사전에서 삭제합니다. (없는 단어 무시)
    """
    if req.list_type not in ['whitelist', 'blacklist']:
        raise HTTPException(status_code=400, detail="list_type 오류")
    
    removed_count = first_filter._update_user_dictionary(req.words, req.list_type, action='remove')
    
    return {
        "status": "success",
        "message": f"{removed_count}개의 단어가 {req.list_type}에서 삭제되었습니다.",
        "processed_count": removed_count,
        "current_total": {
            "whitelist": len(first_filter.user_whitelist),
            "blacklist": len(first_filter.user_blacklist)
        }
    }

@router.get("/config", response_model=SystemConfigResponse, summary="현재 시스템 설정 조회")
async def get_system_config():
    """현재 메모리에 로드된 시스템 설정값을 조회합니다."""
    return {
        "security_level": config.SECURITY_LEVEL,
        "risk_threshold": config.RISK_THRESHOLD,
        "use_detail_ai_model": config.USE_DETAIL_AI_MODEL,
        "enabled_modules": list(config.SPECIAL_AI_MODULES.keys())
    }

@router.patch("/config", summary="시스템 설정 동적 변경 (영구 저장)")
async def update_system_config(settings: SystemConfigUpdate):
    """
    설정을 변경하고 .env 파일에 영구적으로 저장합니다.
    주의: .env 파일이 변경되면 uvicorn이 이를 감지하고 서버를 재시작할 수 있습니다.
    """
    updated_fields = {}
    dotenv_file = find_dotenv()

    # 1. 보안 레벨
    if settings.security_level is not None:
        config.SECURITY_LEVEL = settings.security_level
        set_key(dotenv_file, "SECURITY_LEVEL", str(settings.security_level))
        updated_fields["security_level"] = settings.security_level

    # 2. 위험도 임계값
    if settings.risk_threshold is not None:
        config.RISK_THRESHOLD = settings.risk_threshold
        set_key(dotenv_file, "RISK_THRESHOLD", str(settings.risk_threshold))
        updated_fields["risk_threshold"] = settings.risk_threshold

    # 3. 정밀 AI 모델 사용 여부
    if settings.use_detail_ai is not None:
        config.USE_DETAIL_AI_MODEL = settings.use_detail_ai
        set_key(dotenv_file, "USE_DETAIL_AI_MODEL", str(settings.use_detail_ai))
        updated_fields["use_detail_ai_model"] = settings.use_detail_ai

    # 4. 활성 모듈
    if settings.enabled_modules is not None: 
        new_modules = {}
        valid_keys = []
        for key in settings.enabled_modules: 
            key_upper = key.upper()
            if key_upper in config._SPECIAL_AI_MODULE_DEFINITIONS:
                new_modules[key_upper] = config._SPECIAL_AI_MODULE_DEFINITIONS[key_upper]
                valid_keys.append(key_upper)
        
        config.SPECIAL_AI_MODULES = new_modules
        modules_str = ",".join(valid_keys)
        set_key(dotenv_file, "ENABLED_MODULES", modules_str) 
        updated_fields["enabled_modules"] = valid_keys

    return {
        "status": "updated",
        "updated_fields": updated_fields,
        "current_config": {
            "security_level": config.SECURITY_LEVEL,
            "risk_threshold": config.RISK_THRESHOLD,
            "enabled_modules": list(config.SPECIAL_AI_MODULES.keys())
        }
    }