import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from fastapi.encoders import jsonable_encoder

from app.database import SessionLocal
from app.routers.deps import get_user_from_token
from app.services.snapshot_service import build_snapshot


router = APIRouter(tags=["websocket"])
logger = logging.getLogger(__name__)


@router.websocket("/ws/metrics")
async def metrics_socket(websocket: WebSocket, token: str | None = None) -> None:
    await websocket.accept()
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    with SessionLocal() as db:
        user = get_user_from_token(db, token)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    try:
        while True:
            try:
                with SessionLocal() as db:
                    scoped_user = get_user_from_token(db, token)
                    snapshot = build_snapshot(db, scoped_user)
                await websocket.send_json(jsonable_encoder(snapshot))
            except WebSocketDisconnect:
                raise
            except Exception:
                logger.exception("WebSocket metrics snapshot failed")
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        return
