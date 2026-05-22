"""치지직 OAuth helper — chzzkpy 우회하고 raw HTTP 로 호출.

chzzkpy 2.x 가 pydantic 2.10+ 와 호환성 이슈가 있어, OAuth 부분은 직접 처리.
"""
from __future__ import annotations

import logging
import os
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/oauth/chzzk", tags=["chzzk-oauth"])

CHZZK_AUTH_BASE = "https://chzzk.naver.com/account-interlock"
CHZZK_TOKEN_API = "https://openapi.chzzk.naver.com/auth/v1/token"
CHZZK_USER_ME = "https://openapi.chzzk.naver.com/open/v1/users/me"


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
