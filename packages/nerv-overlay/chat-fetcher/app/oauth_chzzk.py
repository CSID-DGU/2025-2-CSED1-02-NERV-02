"""치지직 OAuth helper — chzzkpy 우회하고 raw HTTP 로 호출.

chzzkpy 2.x 가 pydantic 2.10+ 와 호환성 이슈가 있어, OAuth 부분은 직접 처리.
"""
from __future__ import annotations

import asyncio
import logging
import os
import secrets
from urllib.parse import urlencode

import httpx
import socketio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/oauth/chzzk", tags=["chzzk-oauth"])

CHZZK_AUTH_BASE = "https://chzzk.naver.com/account-interlock"
CHZZK_TOKEN_API = "https://openapi.chzzk.naver.com/auth/v1/token"
CHZZK_USER_ME = "https://openapi.chzzk.naver.com/open/v1/users/me"
CHZZK_SESSIONS_AUTH = "https://openapi.chzzk.naver.com/open/v1/sessions/auth"
CHZZK_SESSIONS_SUBSCRIBE_CHAT = "https://openapi.chzzk.naver.com/open/v1/sessions/events/subscribe/chat"


def _credentials():
    client_id = os.environ.get("CHZZK_CLIENT_ID")
    client_secret = os.environ.get("CHZZK_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="CHZZK_CLIENT_ID/SECRET 환경변수 미설정")
    return client_id, client_secret


class AuthUrlRequest(BaseModel):
    redirect_url: str
    state: str | None = None


class AuthUrlResponse(BaseModel):
    auth_url: str
    state: str


@router.post("/auth-url", response_model=AuthUrlResponse)
async def auth_url(req: AuthUrlRequest):
    client_id, _ = _credentials()
    state = req.state or secrets.token_urlsafe(16)
    query = urlencode({
        "clientId": client_id,
        "redirectUri": req.redirect_url,
        "state": state,
    })
    url = f"{CHZZK_AUTH_BASE}?{query}"
    return AuthUrlResponse(auth_url=url, state=state)


class ExchangeRequest(BaseModel):
    code: str
    state: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


def _parse_token(payload: dict) -> TokenResponse:
    """CHZZK API 응답: {code, message, content: {accessToken, refreshToken, ...}}"""
    if "content" in payload and isinstance(payload["content"], dict):
        c = payload["content"]
    else:
        c = payload
    return TokenResponse(
        access_token=c["accessToken"],
        refresh_token=c["refreshToken"],
        token_type=c.get("tokenType", "Bearer"),
        expires_in=int(c.get("expiresIn", 3600)),
    )


@router.post("/exchange", response_model=TokenResponse)
async def exchange(req: ExchangeRequest):
    client_id, client_secret = _credentials()
    body = {
        "grantType": "authorization_code",
        "clientId": client_id,
        "clientSecret": client_secret,
        "code": req.code,
        "state": req.state,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.post(CHZZK_TOKEN_API, json=body)
        except Exception as e:
            logger.exception("[CHZZK OAuth] exchange 요청 실패: %s", e)
            raise HTTPException(status_code=502, detail=f"CHZZK 요청 실패: {e}") from e

    if r.status_code >= 400:
        logger.warning("[CHZZK OAuth] exchange %d: %s", r.status_code, r.text[:300])
        raise HTTPException(status_code=400, detail=f"CHZZK {r.status_code}: {r.text[:200]}")

    return _parse_token(r.json())


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest):
    client_id, client_secret = _credentials()
    body = {
        "grantType": "refresh_token",
        "clientId": client_id,
        "clientSecret": client_secret,
        "refreshToken": req.refresh_token,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(CHZZK_TOKEN_API, json=body)
    if r.status_code >= 400:
        logger.warning("[CHZZK OAuth] refresh %d: %s", r.status_code, r.text[:300])
        raise HTTPException(status_code=400, detail=f"CHZZK {r.status_code}: {r.text[:200]}")
    return _parse_token(r.json())


class MeResponse(BaseModel):
    channel_id: str
    channel_name: str | None = None


@router.get("/me", response_model=MeResponse)
async def me(access_token: str):
    """본인 채널 정보 조회. CHZZK OpenAPI users/me 호출.

    응답 예: {"code":200,"content":{"channelId":"...","channelName":"..."}}
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(CHZZK_USER_ME, headers=headers)
        except Exception as e:
            logger.exception("[CHZZK OAuth] me 요청 실패: %s", e)
            raise HTTPException(status_code=502, detail=f"CHZZK 요청 실패: {e}") from e

    if r.status_code >= 400:
        logger.warning("[CHZZK OAuth] me %d: %s", r.status_code, r.text[:300])
        raise HTTPException(status_code=r.status_code, detail=f"CHZZK {r.status_code}: {r.text[:200]}")

    payload = r.json()
    content = payload.get("content", payload) if isinstance(payload, dict) else {}
    channel_id = content.get("channelId") or content.get("channel_id")
    if not channel_id:
        logger.warning("[CHZZK OAuth] me 응답에 channelId 없음: %s", str(payload)[:200])
        raise HTTPException(status_code=502, detail="CHZZK me 응답에 channelId 없음")
    return MeResponse(
        channel_id=channel_id,
        channel_name=content.get("channelName") or content.get("nickname"),
    )


@router.get("/test-session-auth")
async def test_session_auth(access_token: str):
    """검증용 — user access_token 으로 Sessions API auth 호출.

    응답:
    - status: HTTP status
    - body: raw JSON 응답
    - url: 추출된 socket.io URL (성공 시)
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(CHZZK_SESSIONS_AUTH, headers=headers)
        except Exception as e:
            return {"ok": False, "stage": "request", "error": str(e)}

    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text[:500]}

    url = None
    if isinstance(body, dict):
        url = body.get("content", {}).get("url") if isinstance(body.get("content"), dict) else None

    return {
        "ok": r.status_code < 400 and url is not None,
        "status": r.status_code,
        "url": url,
        "body": body,
    }


@router.get("/test-full-flow")
async def test_full_flow(access_token: str, listen_seconds: float = 5.0):
    """검증용 — sessions/auth + socket.io 연결 + subscribe/chat + N초 listen.

    응답:
    - session_auth: sessions/auth 결과
    - session_key: SYSTEM 이벤트에서 받은 키
    - subscribe: subscribe/chat 결과
    - chat_events: listen_seconds 동안 받은 CHAT 이벤트들 (최대 5개)
    """
    result: dict = {
        "session_auth": None,
        "socket_connected": False,
        "session_key": None,
        "subscribe": None,
        "chat_events": [],
        "error": None,
    }

    # 1) sessions/auth
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(CHZZK_SESSIONS_AUTH, headers=headers)
    try:
        auth_body = r.json()
    except Exception:
        auth_body = {"raw": r.text[:300]}
    url = (auth_body.get("content") or {}).get("url") if isinstance(auth_body, dict) else None
    result["session_auth"] = {"status": r.status_code, "url": url}
    if not url:
        result["error"] = "sessions/auth 응답에 url 없음"
        return result

    # 2) socket.io 연결 — chzzkpy 와 동일하게 EIO=3, transport=websocket
    sio = socketio.AsyncClient(reconnection=False, logger=False, engineio_logger=False)
    system_key_evt = asyncio.Event()
    chat_evts: list = []

    @sio.on("SYSTEM")
    async def on_system(data):
        logger.info("[CHZZK-Session] SYSTEM event: %s", str(data)[:200])
        # data 가 dict 일 수도, JSON string 일 수도 — 둘 다 처리
        import json as _json
        payload = data
        if isinstance(data, str):
            try:
                payload = _json.loads(data)
            except Exception:
                payload = {"raw": data}
        # sessionKey 추출 — type=connected 이벤트의 data.sessionKey
        if isinstance(payload, dict):
            inner = payload.get("data", payload)
            if isinstance(inner, dict):
                key = inner.get("sessionKey")
                if key and not result["session_key"]:
                    result["session_key"] = key
                    system_key_evt.set()

    @sio.on("CHAT")
    async def on_chat(data):
        logger.info("[CHZZK-Session] CHAT event: %s", str(data)[:200])
        if len(chat_evts) < 5:
            chat_evts.append(data if isinstance(data, (dict, str)) else str(data))

    try:
        # python-socketio 의 AsyncClient 는 default EIO=4. CHZZK 는 EIO=3.
        # transports=['websocket'] 강제. socketio_path 기본값 'socket.io' OK.
        await sio.connect(url, transports=["websocket"], wait_timeout=10)
        result["socket_connected"] = True

        # SYSTEM 이벤트 대기 (최대 5초)
        try:
            await asyncio.wait_for(system_key_evt.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            result["error"] = "SYSTEM/connected 이벤트 시한 초과"
            await sio.disconnect()
            return result

        # 3) subscribe/chat
        async with httpx.AsyncClient(timeout=10) as client:
            sub = await client.post(
                CHZZK_SESSIONS_SUBSCRIBE_CHAT,
                headers=headers,
                params={"sessionKey": result["session_key"]},
            )
        try:
            sub_body = sub.json()
        except Exception:
            sub_body = {"raw": sub.text[:300]}
        result["subscribe"] = {"status": sub.status_code, "body": sub_body}

        if sub.status_code >= 400:
            await sio.disconnect()
            return result

        # 4) N초 listen
        await asyncio.sleep(listen_seconds)
        result["chat_events"] = chat_evts
    except Exception as e:
        logger.exception("[CHZZK-Session] flow error: %s", e)
        result["error"] = f"{type(e).__name__}: {e}"
    finally:
        try:
            await sio.disconnect()
        except Exception:
            pass

    return result
