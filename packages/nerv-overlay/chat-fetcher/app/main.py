"""FastAPI 채팅 fetcher 서비스.

Endpoints:
- GET  /health                           헬스
- GET  /sources                          활성 채널 목록
- WS   /ws/{source}/{channel_id}         채널 메시지 스트림 (구독)
    source: chzzk | youtube | dummy

WebSocket 모델:
- 동일 (source, channel_id) 는 외부 연결 1개만 유지
- 다수 클라이언트가 같은 채널을 구독해도 fanout
- 마지막 구독자가 떠나면 외부 연결 자동 종료
"""
from __future__ import annotations

import asyncio
import json
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from pydantic import BaseModel

from .hub import registry
from .oauth_chzzk import router as chzzk_oauth_router
from .sources.chzzk import make_chzzk_factory
from .sources.dummy import inject_message, make_dummy_factory

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="nerv-overlay chat-fetcher",
    description="Pulls real chat from CHZZK / YouTube and fans out to subscribers.",
    version="0.1.0",
)
app.include_router(chzzk_oauth_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


class InjectRequest(BaseModel):
    content: str
    author: str = "Tester"


@app.post("/sources/dummy/{channel_id}/inject")
async def inject_to_dummy(channel_id: str, req: InjectRequest):
    """더미 채널에 사용자 정의 메시지 1건 주입 (메인 페이지 테스트용)."""
    sent = await inject_message(channel_id, req.content, req.author)
    return {"injected": sent}


@app.get("/sources")
async def sources():
    items = []
    for (src, cid), hub in registry._hubs.items():  # noqa: SLF001
        items.append({
            "source": src,
            "channel_id": cid,
            "subscribers": len(hub.queues),
            "started": hub._started,  # noqa: SLF001
        })
    return {"sources": items}


def _starter_factory_for(source: str, channel_id: str, access_token: str | None, refresh_token: str | None):
    if source == "chzzk":
        # OAuth Sessions API — access_token 필수 (사용자별 본인 채널 구독)
        return lambda: make_chzzk_factory(channel_id, access_token, refresh_token)
    if source == "dummy":
        return lambda: make_dummy_factory(channel_id)
    raise ValueError(f"Unknown source: {source}")


@app.websocket("/ws/{source}/{channel_id}")
async def stream(
    ws: WebSocket,
    source: str,
    channel_id: str,
    access_token: str | None = None,
    refresh_token: str | None = None,
):
    if source not in ("chzzk", "youtube", "dummy"):
        await ws.close(code=1008, reason=f"unsupported source: {source}")
        return
    if source == "youtube":
        await ws.close(code=1011, reason="youtube not implemented yet")
        return

    await ws.accept()
    logger.info("[WS] subscribe source=%s channel=%s", source, channel_id)

    try:
        async with registry.subscribe(
            source, channel_id,
            _starter_factory_for(source, channel_id, access_token, refresh_token),
        ) as q:
            while True:
                msg = await q.get()
                await ws.send_text(json.dumps(msg, ensure_ascii=False))
    except WebSocketDisconnect:
        logger.info("[WS] disconnect source=%s channel=%s", source, channel_id)
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.exception("[WS] stream error: %s", e)
        try:
            await ws.close(code=1011, reason=str(e))
        except Exception:
            pass
