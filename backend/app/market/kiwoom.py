"""
Kiwoom REST market data adapter.
Endpoint paths verified against live API responses.
"""
import datetime
from typing import AsyncIterator

import httpx
import structlog

from app.broker.kiwoom_auth import get_token
from app.core.config import settings
from app.core.exceptions import BrokerError
from app.market.schemas import Candle, Snapshot

log = structlog.get_logger()

_PATH_STKINFO = "/api/dostk/stkinfo"
_PATH_CHART   = "/api/dostk/chart"

_PERIOD_API_ID = {"D": "ka10081", "W": "ka10082", "M": "ka10083"}
# Kiwoom response array key per period
_PERIOD_RESP_KEY = {
    "D": "stk_dt_pole_chart_qry",
    "W": "stk_stk_pole_chart_qry",   # verified from live API response
    "M": "stk_mth_pole_chart_qry",
}


def _price(raw: str) -> int:
    """Strip Kiwoom's +/- sign prefix and return integer price."""
    return abs(int(raw.replace(",", "")))


def _signed(raw: str) -> int:
    """Parse signed value (e.g. pred_pre '-1500' → -1500)."""
    return int(raw.replace(",", ""))


class KiwoomMarketSource:
    async def _headers(self, api_id: str) -> dict[str, str]:
        token = await get_token()
        return {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"{token.token_type} {token.access_token}",
            "api-id": api_id,
        }

    async def get_snapshot(self, ticker: str) -> Snapshot:
        headers = await self._headers("ka10001")
        async with httpx.AsyncClient(base_url=settings.active_base_url) as client:
            resp = await client.post(
                _PATH_STKINFO,
                headers=headers,
                json={"stk_cd": ticker},
            )
        if resp.status_code != 200:
            raise BrokerError(f"Snapshot failed [{resp.status_code}]: {resp.text}")
        data = resp.json()
        if data.get("return_code", -1) != 0 and "stk_nm" not in data:
            raise BrokerError(f"Snapshot error: {data.get('return_msg')}")

        cur_prc  = _price(data.get("cur_prc", "0"))
        pred_pre = _signed(data.get("pred_pre", "0"))
        base_pric = _price(data.get("base_pric", "1"))
        change_pct = round(pred_pre / base_pric * 100, 2) if base_pric else 0.0

        return Snapshot(
            ticker=ticker,
            name=data.get("stk_nm", ticker),
            price=cur_prc,
            change=pred_pre,
            change_pct=change_pct,
            volume=0,   # ka10001 doesn't include volume; use ka10007 if needed
            market="KOSPI",
            timestamp=datetime.datetime.now(tz=datetime.timezone.utc),
        )

    async def get_candles(self, ticker: str, period: str = "D", count: int = 60) -> list[Candle]:
        return await self.get_daily_candles(ticker, count=count, period=period)

    async def get_daily_candles(self, ticker: str, count: int = 60, period: str = "D") -> list[Candle]:
        api_id = _PERIOD_API_ID.get(period, "ka10081")
        headers = await self._headers(api_id)
        base_dt = datetime.date.today().strftime("%Y%m%d")
        async with httpx.AsyncClient(base_url=settings.active_base_url) as client:
            resp = await client.post(
                _PATH_CHART,
                headers=headers,
                json={
                    "stk_cd": ticker,
                    "base_dt": base_dt,
                    "upd_stkpc_tp": "1",    # 1 = 원주가 (unadjusted)
                },
            )
        if resp.status_code != 200:
            raise BrokerError(f"Daily candles failed [{resp.status_code}]: {resp.text}")
        data = resp.json()
        if data.get("return_code", 0) != 0:
            raise BrokerError(f"Daily candles error: {data.get('return_msg')}")

        resp_key = _PERIOD_RESP_KEY.get(period, "stk_dt_pole_chart_qry")
        rows = (data.get(resp_key) or data.get("stk_dt_pole_chart_qry") or [])[:count]
        candles = []
        for row in reversed(rows):
            try:
                candles.append(Candle(
                    date=datetime.date(
                        int(row["dt"][:4]),
                        int(row["dt"][4:6]),
                        int(row["dt"][6:8]),
                    ),
                    open=_price(row["open_pric"]),
                    high=_price(row["high_pric"]),
                    low=_price(row["low_pric"]),
                    close=_price(row["cur_prc"]),
                    volume=int(row.get("trde_qty", 0)),
                ))
            except (KeyError, ValueError):
                continue
        return candles

    async def stream_snapshots(self, tickers: list[str]) -> AsyncIterator[dict[str, Snapshot]]:
        """Polling fallback — real WebSocket implementation is M3+."""
        import asyncio
        while True:
            batch = {}
            for ticker in tickers:
                try:
                    batch[ticker] = await self.get_snapshot(ticker)
                except BrokerError as e:
                    log.warning("kiwoom.snapshot.error", ticker=ticker, error=str(e))
            if batch:
                yield batch
            await asyncio.sleep(3)
