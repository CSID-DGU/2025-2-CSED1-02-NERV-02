import sys
import os
from dotenv import set_key, find_dotenv

from fastapi import FastAPI, HTTPException, Body, Query
from starlette.middleware.cors import CORSMiddleware
from schemas import *

try:
    from config import config
    from filter_api.core.first_pass_filter import FirstPassFilter
    from filter_api.core.second_pass_filter import SecondPassFilter
    from filter_api.core.risk_scorer import RiskScorer
    from filter_api.core.policy_manager import PolicyManager
    from filter_api.clients.youtube_client import YouTubeClient
except ImportError as e:
    print(f"[System] 필수 모듈 임포트 실패: {e}")
    sys.exit(1)

app = FastAPI(
    title="YouTube Comment Filtering System API",
    description="1차/2차/위험도/정책 모델을 엄격하게 분리하여 단계별 데이터 변화를 명확히 보여주는 API",
    version="1.0.2",
    openapi_version="3.0.2"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("[System] 모듈 초기화 중...")
try:
    first_filter = FirstPassFilter()
    second_filter = SecondPassFilter()
    risk_scorer = RiskScorer()
    policy_manager = PolicyManager()
    yt_client = YouTubeClient()
    print("[System] 서버 준비 완료.")
except Exception as e:
    print(f"[System] 초기화 중 오류 발생: {e}")
    sys.exit(1)

# =========================================================
# [API 1] 시스템 설정 관리 API (System Config APIs)
# =========================================================

@app.get("/api/system/dictionary", response_model=DictionaryResponse, summary="사용자 사전 목록 조회")
async def get_dictionary_list(
    list_type: str = Query(..., description="조회할 타입 ('whitelist' 또는 'blacklist')")
):
    """
    사용자 사전 목록을 조회합니다. list_type('whitelist', 'blacklist')을 지정해야 합니다.
    """
    if list_type not in ['whitelist', 'blacklist']:
        raise HTTPException(status_code=400, detail="list_type은 'whitelist' 또는 'blacklist'여야 합니다.")

    # 데이터 가져오기
    data = first_filter.get_user_dictionary(list_type)
    
    whitelist = data.get('whitelist', [])
    blacklist = data.get('blacklist', [])
    
    return {
        "whitelist": whitelist,
        "blacklist": blacklist,
        "total_count": len(whitelist) + len(blacklist)
    }

@app.post("/api/system/dictionary", response_model=DictionaryUpdateResponse, summary="단어 일괄 추가 (배열)")
async def add_dictionary_words(req: DictionaryRequest):
    """
    여러 단어를 리스트로 받아 사전에 추가합니다. (중복 무시)
    """
    if req.list_type not in ['whitelist', 'blacklist']:
        raise HTTPException(status_code=400, detail="list_type 오류")
    
    # 추가 함수 호출 (action='add')
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

@app.delete("/api/system/dictionary", response_model=DictionaryUpdateResponse, summary="단어 일괄 삭제 (배열)")
async def remove_dictionary_words(req: DictionaryRequest):
    """
    여러 단어를 리스트로 받아 사전에서 삭제합니다. (없는 단어 무시)
    """
    if req.list_type not in ['whitelist', 'blacklist']:
        raise HTTPException(status_code=400, detail="list_type 오류")
    
    # 삭제 함수 호출 (action='remove')
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

@app.get("/api/system/config", response_model=SystemConfigResponse, summary="현재 시스템 설정 조회")
async def get_system_config():
    """현재 메모리에 로드된 시스템 설정값을 조회합니다."""
    return {
        "security_level": config.SECURITY_LEVEL,
        "risk_threshold": config.RISK_THRESHOLD,
        "use_detail_ai_model": config.USE_DETAIL_AI_MODEL,
        "enabled_modules": list(config.SPECIAL_AI_MODULES.keys())
    }

@app.patch("/api/system/config", summary="시스템 설정 동적 변경 (영구 저장)")
async def update_system_config(settings: SystemConfigUpdate):
    """
    설정을 변경하고 .env 파일에 영구적으로 저장합니다.
    주의: .env 파일이 변경되면 uvicorn이 이를 감지하고 서버를 재시작할 수 있습니다.
    """
    updated_fields = {}
    dotenv_file = find_dotenv()

    # 1. 보안 레벨 변경
    if settings.security_level is not None:
        config.SECURITY_LEVEL = settings.security_level
        set_key(dotenv_file, "SECURITY_LEVEL", str(settings.security_level))
        updated_fields["security_level"] = settings.security_level

    # 2. 위험도 임계값 변경
    if settings.risk_threshold is not None:
        config.RISK_THRESHOLD = settings.risk_threshold
        set_key(dotenv_file, "RISK_THRESHOLD", str(settings.risk_threshold))
        updated_fields["risk_threshold"] = settings.risk_threshold

    # 3. 정밀 AI 모델 사용 여부 변경
    if settings.use_detail_ai is not None:
        config.USE_DETAIL_AI_MODEL = settings.use_detail_ai
        set_key(dotenv_file, "USE_DETAIL_AI_MODEL", str(settings.use_detail_ai))
        updated_fields["use_detail_ai_model"] = settings.use_detail_ai

    # 4. 활성 모듈 변경
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
        "status": "updated (saved to .env)",
        "updated_fields": updated_fields,
        "current_config": {
            "security_level": config.SECURITY_LEVEL,
            "risk_threshold": config.RISK_THRESHOLD,
            "enabled_modules": list(config.SPECIAL_AI_MODULES.keys())
        }
    }           


# =========================================================
# [API 2] 개별 모듈 테스트 (Unit APIs)
# =========================================================

@app.post("/api/modules/first-pass", response_model=FirstPassResponse, summary="Step 1. 1차 필터링")
async def run_first_pass(input_data: TextInput):
    """
    KoNLPy 및 사전을 이용한 1차 필터링을 수행합니다.
    반환값은 FirstPassResponse 모델을 따릅니다.
    """
    try:
        result = first_filter.execute(input_data.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/modules/second-pass", response_model=SecondPassResponse, summary="Step 2. 2차 필터링 (AI)")
async def run_second_pass(
    first_pass_result: FirstPassResponse = Body(
        ...,
        # [입력 예시] 1차 필터 결과 모델을 그대로 사용 (욕설만 잡힌 상태)
        json_schema_extra={
            "example": {
                "original_text": "야이 개새끼야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라",
                "status": "FILTERED_BY_FIRST_PASS",
                "detected_words": [{"word": "개새끼", "type": "SYSTEM_KEYWORD"}],
                "text_for_filtering": "야이 __F__야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라"
            }
        }
    )
):
    """
    1차 필터링 결과(FirstPassResponse)를 입력받아 AI 정밀 분석을 수행합니다.
    반환값은 SecondPassResponse 모델을 따르며, AI 적발 내역이 누적됩니다.
    """
    try:
        # Pydantic 모델 -> dict 변환
        input_dict = first_pass_result.dict()
        result = second_filter.execute(input_dict)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/modules/score", response_model=RiskResponse, summary="Step 3. 위험도 점수 계산")
async def calculate_risk_score(
    filter_result: SecondPassResponse = Body(
        ...,
        # [입력 예시] 2차 필터까지 완료된 상태 (모든 적발 내역 포함)
        json_schema_extra={
            "example": {
                "original_text": "야이 개새끼야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라",
                "status": "FILTERED_BY_SECOND_PASS",
                "detected_words": [
                    {"word": "개새끼", "type": "SYSTEM_KEYWORD"},
                    {"word": "니네 집 주소 다 털었다", "type": "AI_AGGRESSION"},
                    {"word": "010-1234-5678", "type": "AI_PRIVACY"}
                ],
                "text_for_filtering": "야이 __F__야 ㅋㅋ __S__ __S__ __S__"
            }
        }
    )
):
    try:
        input_dict = filter_result.dict()
        score = risk_scorer.execute(input_dict)
        return {"risk_score": score}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/modules/policy", response_model=PolicyResponse, summary="Step 4. 최종 처분 결정")
async def decide_policy(
    data: PolicyInput = Body(
        ...,
        # [입력 예시] 계산된 점수와 최종 필터링 결과
        json_schema_extra={
            "example": {
                "risk_score": 0.98,
                "filter_result": {
                    "original_text": "야이 개새끼야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라",
                    "status": "FILTERED_BY_SECOND_PASS",
                    "detected_words": [
                        {"word": "개새끼", "type": "SYSTEM_KEYWORD"},
                        {"word": "니네 집 주소 다 털었다", "type": "AI_AGGRESSION"},
                        {"word": "010-1234-5678", "type": "AI_PRIVACY"}
                    ],
                    "text_for_filtering": "야이 __F__야 ㅋㅋ __S__ __S__ __S__"
                }
            }
        }
    )
):
    try:
        score = data.risk_score
        f_res = data.filter_result.dict()
        decision = policy_manager.decide_action(score, f_res)
        return decision
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- [YouTube 단순 조회용 API] ---

@app.get("/api/modules/youtube/video", summary="유튜브 영상 메타데이터 조회")
async def get_youtube_video_info(video_id: str):
    if not yt_client.youtube:
        raise HTTPException(status_code=500, detail="YouTube API 클라이언트가 초기화되지 않았습니다.")
    return yt_client.get_video_details(video_id)

@app.get("/api/modules/youtube/comments", summary="유튜브 댓글 수집 (원문)")
async def get_youtube_comments_raw(video_id: str, max_pages: int = 1):
    if not yt_client.youtube:
        raise HTTPException(status_code=500, detail="YouTube API 클라이언트가 초기화되지 않았습니다.")
    comments = yt_client.get_comments(video_id, max_pages=max_pages)
    return {"video_id": video_id, "total_count": len(comments), "comments": comments}

# =========================================================
# [API 3] 전체 통합 워크플로우 (Workflow APIs)
# =========================================================

def _run_pipeline(text: str) -> dict:
    res = first_filter.execute(text)
    res = second_filter.execute(res)
    score = risk_scorer.execute(res)
    final_decision = policy_manager.decide_action(score, res)
    
    return {
        "original_text": res['original_text'],
        "processed_text": final_decision['processed_text'],
        "action": final_decision['action'],
        "score": score,
        "details": res
    }

@app.post("/api/workflow/analyze-text", response_model=AnalysisResult, summary="단일 텍스트 전체 분석")
async def analyze_single_text(
    input_data: TextInput = Body(
        ...,
        json_schema_extra={
            "example": {"text": "야이 개새끼야 ㅋㅋ 니네 집 주소 다 털었다 010-1234-5678 밤길 조심해라"}
        }
    )
):
    try:
        result = _run_pipeline(input_data.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/workflow/analyze-youtube", response_model=YoutubeAnalysisResponse, summary="유튜브 영상 댓글 분석")
async def analyze_youtube_video(video_id: str, max_pages: int = 1):
    if not yt_client.youtube:
        raise HTTPException(status_code=500, detail="YouTube API 연결 실패 (API Key 확인 필요)")
    
    video_info = yt_client.get_video_details(video_id)
    comments = yt_client.get_comments(video_id, max_pages=max_pages)
    
    analyzed_results = []
    blocked_count = 0
    
    for comm in comments:
        text = comm['text_original']
        analysis = _run_pipeline(text)
        
        summary = {
            "author": comm['author_display_name'],
            "published_at": comm['published_at'],
            "original": text,
            "processed": analysis['processed_text'],
            "action": analysis['action'],
            "risk_score": analysis['score'],
            "violation_tags": [item['type'] for item in analysis['details']['detected_words']]
        }
        analyzed_results.append(summary)
        
        if analysis['action'] != "PASS":
            blocked_count += 1

    video_title = "Unknown Video"
    if video_info and isinstance(video_info, dict):
        video_title = video_info.get('snippet', {}).get('title', 'Unknown Video')

    return {
        "video_info": {"title": video_title, "id": video_id},
        "stats": {"total_comments": len(comments), "blocked_comments": blocked_count, "clean_comments": len(comments) - blocked_count},
        "results": analyzed_results
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    # Swagger UI (Docs): http://localhost:8000/docs