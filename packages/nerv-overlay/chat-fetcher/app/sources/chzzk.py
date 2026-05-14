"""치지직 채팅 어댑터 — 공식 OpenAPI Sessions/Subscribe 기반.

흐름:
1) GET /open/v1/sessions/auth (Bearer user access_token) → socket.io URL
2) socket.io connect (transports=websocket)
3) "system"/"connected" 이벤트로 sessionKey 캡처
4) POST /open/v1/sessions/events/subscribe/chat?sessionKey=...
5) "chat" 이벤트 마다 publish 호출

각 사용자 본인 OAuth 토큰으로 본인 채널만 구독 (CHZZK 정책).
NID_AUT/NID_SES 비공식 쿠키 의존성 제거.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Awaitable, Callable

import httpx
import socketio

logger = logging.getLogger(__name__)

CHZZK_SESSIONS_AUTH = "https://openapi.chzzk.naver.com/open/v1/sessions/auth"
CHZZK_SESSIONS_SUBSCRIBE_CHAT = "https://openapi.chzzk.naver.com/open/v1/sessions/events/subscribe/chat"
CHZZK_SESSIONS_UNSUBSCRIBE_CHAT = "https://openapi.chzzk.naver.com/open/v1/sessions/events/unsubscribe/chat"


class ChzzkSession:
    def __init__(self, channel_id: str, access_token: str):
        self.channel_id = channel_id
        self.access_token = access_token
        self.sio: socketio.AsyncClient | None = None
        self.session_key: str | None = None
        self._connected_evt = asyncio.Event()
        self._on_message: Callable[[dict], Awaitable[None]] | None = None

    async def start(self, on_message: Callable[[dict], Awaitable[None]]) -> None:
        self._on_message = on_message
        url = await self._get_session_url()

        self.sio = socketio.AsyncClient(reconnection=False, logger=False, engineio_logger=False)
        self._wire_handlers(self.sio)
        await self.sio.connect(url, transports=["websocket"], wait_timeout=10)

        try:
            await asyncio.wait_for(self._connected_evt.wait(), timeout=10)
        except asyncio.TimeoutError as e:
            await self.sio.disconnect()
            raise RuntimeError("CHZZK system/connected 이벤트 시한 초과") from e

        await self._subscribe_chat()
        logger.info("[CHZZK-Session] start 완료 channel=%s sessionKey=%s",
                    self.channel_id, self.session_key)

    async def _get_session_url(self) -> str:
        headers = {"Authorization": f"Bearer {self.access_token}"}
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(CHZZK_SESSIONS_AUTH, headers=headers)
        if r.status_code >= 400:
            raise RuntimeError(f"sessions/auth {r.status_code}: {r.text[:200]}")
        body = r.json()
        url = (body.get("content") or {}).get("url") if isinstance(body.get("content"), dict) else None
        if not url:
            raise RuntimeError(f"sessions/auth 응답에 url 없음: {str(body)[:200]}")
        return url

    async def _subscribe_chat(self) -> None:
        headers = {"Authorization": f"Bearer {self.access_token}"}
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                CHZZK_SESSIONS_SUBSCRIBE_CHAT,
                headers=headers,
                params={"sessionKey": self.session_key},
            )
        if r.status_code >= 400:
            raise RuntimeError(f"subscribe/chat {r.status_code}: {r.text[:200]}")

    def _wire_handlers(self, sio: socketio.AsyncClient) -> None:
        # chzzkpy state.py 기준 이벤트 이름은 소문자(system/chat). 안전을 위해 양쪽 등록.
        for name in ("system", "SYSTEM"):
            sio.on(name, self._on_system)
        for name in ("chat", "CHAT"):
            sio.on(name, self._on_chat)

    async def _on_system(self, data) -> None:
        try:
            payload = json.loads(data) if isinstance(data, str) else data
            if not isinstance(payload, dict):
                return
            evt_type = payload.get("type")
            evt_data = payload.get("data") or {}
            if evt_type == "connected":
                key = evt_data.get("sessionKey") if isinstance(evt_data, dict) else None
                if key and not self.session_key:
                    self.session_key = key
                    self._connected_evt.set()
        except Exception as e:
            logger.warning("[CHZZK-Session] system 파싱 실패: %s", e)

    async def _on_chat(self, data) -> None:
        try:
            payload = json.loads(data) if isinstance(data, str) else data
            if not isinstance(payload, dict):
                logger.debug("[CHZZK-Session] chat non-dict 페이로드: %s", str(data)[:200])
                return
            content = payload.get("content")
            if not content:
                return
            profile = payload.get("profile") or {}
            msg_id = f"chzzk-{payload.get('messageTime', 0)}-{payload.get('senderChannelId', '')}"
            normalized = {
                "id": msg_id,
                "author": profile.get("nickname", "Anonymous"),
                "content": content,
                "ts_received_ms": int(time.time() * 1000),
                "source": "chzzk",
                "channel_id": payload.get("channelId") or self.channel_id,
            }
            if self._on_message:
                await self._on_message(normalized)
        except Exception as e:
            logger.exception("[CHZZK-Session] chat 핸들러 오류: %s", e)

    async def close(self) -> None:
        # best-effort unsubscribe
        if self.sio and self.session_key:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            try:
                async with httpx.AsyncClient(timeout=5) as c:
                    await c.post(
                        CHZZK_SESSIONS_UNSUBSCRIBE_CHAT,
                        headers=headers,
                        params={"sessionKey": self.session_key},
                    )
            except Exception as e:
                logger.debug("[CHZZK-Session] unsubscribe 실패(무시): %s", e)
        if self.sio:
            try:
                await self.sio.disconnect()
            except Exception:
                pass


_active: dict[str, ChzzkSession] = {}


def make_chzzk_factory(
    channel_id: str,
    access_token: str | None = None,
    refresh_token: str | None = None,  # noqa: ARG001 — 향후 자동 갱신용
):
    """ChannelHub 호환 (starter, closer) 페어 생성.

    OAuth Sessions API 사용. access_token 필수 (사용자별 본인 채널만 구독 가능).
    """
    if not access_token:
        raise RuntimeError("CHZZK source 에는 access_token 필요 (사용자 OAuth 인증 필요).")

    async def starter(channel_id_in: str, publish: Callable[[dict], Awaitable[None]]) -> None:
        if channel_id_in in _active:
            return
        sess = ChzzkSession(channel_id_in, access_token)
        _active[channel_id_in] = sess
        try:
            await sess.start(publish)
        except Exception:
            _active.pop(channel_id_in, None)
            raise

    async def closer() -> None:
        sess = _active.pop(channel_id, None)
        if sess:
            await sess.close()

    return starter, closer
