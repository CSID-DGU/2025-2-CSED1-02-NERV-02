"""치지직 채팅 어댑터 — chzzkpy 의 UserClient gateway 기반.

흐름:
1) Client(client_id, client_secret) 생성
2) refresh_user_client(refresh_token) 으로 user_client 발급 (access_token 자동 refresh)
3) on_chat 이벤트 핸들러 등록
4) user_client.connect(UserPermission(chat=True)) 로 socket.io (EIO=3) 연결 + chat 이벤트 수신

각 사용자 본인 OAuth 토큰으로 본인 채널만 구독 (CHZZK 정책).
NID_AUT/NID_SES 비공식 쿠키 의존성 제거.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)


class ChzzkSession:
    def __init__(self, channel_id: str, access_token: str, refresh_token: str):
        self.channel_id = channel_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client = None
        self.user_client = None
        self.task: asyncio.Task | None = None
        self._on_message: Callable[[dict], Awaitable[None]] | None = None

    async def start(self, on_message: Callable[[dict], Awaitable[None]]) -> None:
        # import here so import-time chzzkpy load 실패가 다른 source 에 영향 안 주게
        from chzzkpy import Client, UserPermission

        client_id = os.environ.get("CHZZK_CLIENT_ID")
        client_secret = os.environ.get("CHZZK_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise RuntimeError("CHZZK_CLIENT_ID / CHZZK_CLIENT_SECRET 환경변수 필요")

        self._on_message = on_message
        self.client = Client(client_id, client_secret)

        @self.client.event
        async def on_chat(message):
            try:
                content = getattr(message, "content", None)
                if not content:
                    return
                profile = getattr(message, "profile", None)
                nickname = getattr(profile, "nickname", "Anonymous") if profile else "Anonymous"
                user_id = getattr(message, "user_id", "") or ""
                created = getattr(message, "created_time", None)
                ts_key = int(created.timestamp() * 1000) if created else int(time.time() * 1000)

                normalized = {
                    "id": f"chzzk-{ts_key}-{user_id}",
                    "author": nickname,
                    "content": content,
                    "ts_received_ms": int(time.time() * 1000),
                    "source": "chzzk",
                    "channel_id": getattr(message, "channel", self.channel_id),
                }
                if self._on_message:
                    await self._on_message(normalized)
            except Exception as e:
                logger.exception("[CHZZK] on_chat 핸들러 오류: %s", e)

        @self.client.event
        async def on_connect(session_id):
            logger.info("[CHZZK] gateway connected channel=%s session=%s",
                        self.channel_id, session_id)

        # refresh_token 으로 새 access_token 받고 user_client 발급
        try:
            self.user_client = await self.client.refresh_user_client(self.refresh_token)
        except Exception as e:
            logger.error("[CHZZK] refresh_user_client 실패: %s", e)
            raise

        # connect 는 blocking — background task 로 실행
        self.task = asyncio.create_task(self._connect_loop(UserPermission))

    async def _connect_loop(self, UserPermission) -> None:
        try:
            await self.user_client.connect(UserPermission(chat=True))
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception("[CHZZK] connect 종료: %s", e)

    async def close(self) -> None:
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except (asyncio.CancelledError, Exception):
                pass
        if self.user_client:
            try:
                await self.user_client.disconnect()
            except Exception:
                pass
        if self.client:
            try:
                await self.client.disconnect()
            except Exception:
                pass


_active: dict[str, ChzzkSession] = {}


def make_chzzk_factory(
    channel_id: str,
    access_token: str | None = None,
    refresh_token: str | None = None,
):
    """ChannelHub 호환 (starter, closer) 페어 생성.

    chzzkpy 사용. refresh_token 필수 (access_token 도 같이 받지만 갱신은 chzzkpy 가 처리).
    """
    if not refresh_token:
        raise RuntimeError("CHZZK source 에는 refresh_token 필요 (사용자 OAuth 인증 필요).")

    async def starter(channel_id_in: str, publish: Callable[[dict], Awaitable[None]]) -> None:
        if channel_id_in in _active:
            return
        sess = ChzzkSession(channel_id_in, access_token or "", refresh_token)
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
