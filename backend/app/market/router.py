import asyncio
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from app.db.engine import get_session
from app.market import service
from app.market.schemas import Candle, Snapshot, WatchlistItem

log = structlog.get_logger()
router = APIRouter(prefix="/api/v1/market", tags=["market"])


# ── REST ──────────────────────────────────────────────────────────────────────

@router.get("/snapshot/{ticker}", response_model=Snapshot)
async def get_snapshot(ticker: str):
    src = service.get_source()
    try:
        return await src.get_snapshot(ticker)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown ticker: {ticker}")


@router.get("/candles/{ticker}", response_model=list[Candle])
async def get_candles(ticker: str, period: str = "D", count: int = 60):
    """period: D=일봉, W=주봉, M=월봉"""
    if period not in ("D", "W", "M"):
        raise HTTPException(status_code=400, detail="period must be D, W, or M")
    src = service.get_source()
    try:
        return await src.get_candles(ticker, period=period, count=min(count, 500))
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown ticker: {ticker}")


@router.get("/watchlist", response_model=list[WatchlistItem])
async def get_watchlist():
    return service.list_watchlist()


@router.post("/watchlist/{ticker}", status_code=201)
async def add_watchlist(ticker: str):
    with get_session() as session:
        added = service.add_to_watchlist(ticker, session)
    return {"added": added, "ticker": ticker}


@router.delete("/watchlist/{ticker}")
async def remove_watchlist(ticker: str):
    with get_session() as session:
        removed = service.remove_from_watchlist(ticker, session)
    if not removed:
        raise HTTPException(status_code=404, detail=f"{ticker} not in watchlist")
    return {"removed": True, "ticker": ticker}


# ── WebSocket ─────────────────────────────────────────────────────────────────

class _ConnectionManager:
    def __init__(self) -> None:
        self._active: dict[WebSocket, set[str]] = {}

    async def connect(self, ws: WebSocket, tickers: list[str]) -> None:
        await ws.accept()
        self._active[ws] = set(tickers)
        log.info("ws.connect", tickers=tickers, total=len(self._active))

    def disconnect(self, ws: WebSocket) -> None:
        self._active.pop(ws, None)
        log.info("ws.disconnect", total=len(self._active))

    def update_subscriptions(self, ws: WebSocket, tickers: list[str]) -> None:
        if ws in self._active:
            self._active[ws] = set(tickers)

    async def broadcast(self, snapshots: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        for ws, tickers in self._active.items():
            payload = {t: snapshots[t] for t in tickers if t in snapshots}
            if not payload:
                continue
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    @property
    def all_subscribed_tickers(self) -> list[str]:
        seen: set[str] = set()
        for tickers in self._active.values():
            seen |= tickers
        return list(seen)


manager = _ConnectionManager()
_broadcaster_task: asyncio.Task | None = None


async def start_broadcaster() -> None:
    global _broadcaster_task
    _broadcaster_task = asyncio.create_task(_run_broadcaster())


async def stop_broadcaster() -> None:
    if _broadcaster_task:
        _broadcaster_task.cancel()


async def _run_broadcaster() -> None:
    src = service.get_source()
    # Pull tickers from watchlist + any WS subscribers
    base_tickers = service.get_watchlist_tickers()
    async for batch in src.stream_snapshots(base_tickers):
        payload = {t: s.model_dump(mode="json") for t, s in batch.items()}
        await manager.broadcast(payload)


@router.websocket("/ws")
async def market_ws(websocket: WebSocket):
    tickers = service.get_watchlist_tickers()
    await manager.connect(websocket, tickers)
    try:
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_json(), timeout=30)
                if isinstance(msg, dict) and "tickers" in msg:
                    manager.update_subscriptions(websocket, msg["tickers"])
            except asyncio.TimeoutError:
                await websocket.send_json({"ping": True})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
