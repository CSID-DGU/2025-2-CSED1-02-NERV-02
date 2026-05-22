"""채널별 Pub/Sub 허브 — 한 채널의 채팅을 여러 구독자에게 fanout.

CHZZK/YouTube 연결은 채널당 1개만 유지 (refcount 로 관리).
구독자가 0이 되면 외부 연결 자동 종료.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)


@dataclass
class ChannelHub:
    """1개 채널에 대한 fanout 허브."""

    channel_id: str
    queues: list[asyncio.Queue] = field(default_factory=list)
    starter: Callable[[str, Callable[[dict], Awaitable[None]]], Awaitable[None]] | None = None
    closer: Callable[[], Awaitable[None]] | None = None
    # starter 가 실패하면 호출 — registry 가 이 hub 를 캐시에서 제거 (stale 토큰 방지)
    on_failure: Callable[[], Awaitable[None]] | None = None
    _started: bool = False
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def publish(self, message: dict) -> None:
        """수집된 메시지를 모든 구독 큐에 fanout. 큐 가득 차면 1건 drop."""
        for q in list(self.queues):
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                logger.warning("[Hub] queue full, dropping message for channel=%s", self.channel_id)

    async def attach(self, queue: asyncio.Queue) -> None:
        async with self._lock:
            self.queues.append(queue)
            if not self._started and self.starter:
                self._started = True
                # 외부 연결 시작은 별도 태스크로 (구독자 응답 지연 방지)
                asyncio.create_task(self._safe_start())

    async def detach(self, queue: asyncio.Queue) -> None:
        async with self._lock:
            try:
                self.queues.remove(queue)
            except ValueError:
                pass
            if not self.queues and self._started and self.closer:
                self._started = False
                asyncio.create_task(self._safe_close())

    async def _safe_start(self) -> None:
        try:
            assert self.starter is not None
            await self.starter(self.channel_id, self.publish)
            logger.info("[Hub] started external connection for channel=%s", self.channel_id)
        except Exception as e:
            logger.exception("[Hub] start failed for channel=%s: %s", self.channel_id, e)
            # 실패한 hub 는 stale (옛 토큰 클로저). 캐시에서 제거해 다음 연결이
            # 새 starter(새 토큰)로 hub 를 재생성하도록 한다.
            self._started = False
            if self.on_failure is not None:
                try:
                    await self.on_failure()
                except Exception:
                    logger.exception("[Hub] on_failure cleanup failed channel=%s", self.channel_id)

    async def _safe_close(self) -> None:
        try:
            assert self.closer is not None
            await self.closer()
            logger.info("[Hub] closed external connection for channel=%s", self.channel_id)
        except Exception as e:
            logger.exception("[Hub] close failed for channel=%s: %s", self.channel_id, e)


class HubRegistry:
    """source(chzzk/youtube) × channel_id → ChannelHub 매핑."""

    def __init__(self):
        self._hubs: dict[tuple[str, str], ChannelHub] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(
        self,
        source: str,
        channel_id: str,
        starter_factory: Callable[[], tuple[
            Callable[[str, Callable[[dict], Awaitable[None]]], Awaitable[None]],
            Callable[[], Awaitable[None]],
        ]],
    ) -> ChannelHub:
        key = (source, channel_id)
        async with self._lock:
            hub = self._hubs.get(key)
            if hub is None:
                starter, closer = starter_factory()
                hub = ChannelHub(channel_id=channel_id, starter=starter, closer=closer)
                hub.on_failure = lambda k=key: self._remove(k)
                self._hubs[key] = hub
            return hub

    async def _remove(self, key: tuple[str, str]) -> None:
        async with self._lock:
            self._hubs.pop(key, None)
        logger.info("[Hub] removed stale hub %s", key)

    @asynccontextmanager
    async def subscribe(
        self,
        source: str,
        channel_id: str,
        starter_factory: Callable[[], tuple[
            Callable[[str, Callable[[dict], Awaitable[None]]], Awaitable[None]],
            Callable[[], Awaitable[None]],
        ]],
        max_queue_size: int = 100,
    ) -> AsyncIterator[asyncio.Queue]:
        hub = await self.get_or_create(source, channel_id, starter_factory)
        q: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        await hub.attach(q)
        try:
            yield q
        finally:
            await hub.detach(q)


registry = HubRegistry()
