"""테스트용 더미 채널 — 1초 간격으로 임의 메시지 발생.

실제 CHZZK/YouTube 통합 검증 전에 hub/구독 흐름을 확인하는 용도.
"""
from __future__ import annotations

import asyncio
import random
import time
from typing import Awaitable, Callable

_SAMPLES = [
    "안녕하세요!",
    "오늘 방송 잼있네요",
    "이 시발 진짜",
    "병신같은 플레이",
    "보지 못했어요",
    "씨발 또야?",
    "구독했습니다",
]

_tasks: dict[str, asyncio.Task] = {}


async def _loop(channel_id: str, publish: Callable[[dict], Awaitable[None]]):
    seq = 0
    try:
        while True:
            await asyncio.sleep(random.uniform(0.8, 1.5))
            seq += 1
            await publish({
                "id": f"dummy-{channel_id}-{seq}",
                "author": f"User{random.randint(1, 100)}",
                "content": random.choice(_SAMPLES),
                "ts_received_ms": int(time.time() * 1000),
                "source": "dummy",
                "channel_id": channel_id,
            })
    except asyncio.CancelledError:
        raise


def make_dummy_factory(channel_id: str):
    async def starter(cid: str, publish: Callable[[dict], Awaitable[None]]):
        if cid in _tasks:
            return
        _tasks[cid] = asyncio.create_task(_loop(cid, publish))

    async def closer():
        t = _tasks.pop(channel_id, None)
        if t and not t.done():
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass

    return starter, closer


# ─────────────────────────────────────
# 사용자 주입 메시지 — 메인 페이지의 채팅 입력바에서 호출
# ─────────────────────────────────────
async def inject_message(channel_id: str, content: str, author: str = "Tester") -> bool:
    """해당 채널의 활성 hub 에 메시지 1회 주입. 활성 구독자가 없으면 False 반환."""
    from ..hub import registry
    hub = registry._hubs.get(("dummy", channel_id))
    if hub is None or not hub.queues:
        return False
    await hub.publish({
        "id": f"inject-{int(time.time() * 1000)}-{random.randint(1000, 9999)}",
        "author": author,
        "content": content,
        "ts_received_ms": int(time.time() * 1000),
        "source": "dummy",
        "channel_id": channel_id,
    })
    return True
