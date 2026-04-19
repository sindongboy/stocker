"""
Kiwoom order placement adapter.

Paper mode: simulates an immediate fill at the proposed price (no real API call).
Live mode: calls Kiwoom REST order endpoint.
  ⚠️  Live endpoint path and request schema must be verified against official docs
  before deploying. Add verified params to knowledge/kiwoom-api/order-placement.md.
"""
import uuid
from dataclasses import dataclass

import httpx
import structlog

from app.broker.kiwoom_auth import get_token
from app.core.config import settings
from app.core.exceptions import BrokerError

log = structlog.get_logger()

# TODO: verify against Kiwoom OpenAPI docs before enabling live mode
_ORDER_PATH = "/api/dostk/order"


@dataclass
class OrderResult:
    order_no: str
    fill_price: int
    simulated: bool = False


async def place_limit_order(
    ticker: str,
    side: str,  # "buy" | "sell"
    qty: int,
    price: int,
) -> OrderResult:
    if settings.trading_mode != "live":
        return _paper_fill(ticker, side, qty, price)
    return await _live_order(ticker, side, qty, price)


def _paper_fill(ticker: str, side: str, qty: int, price: int) -> OrderResult:
    order_no = f"PAPER-{uuid.uuid4().hex[:8].upper()}"
    log.info(
        "order.paper_fill",
        ticker=ticker, side=side, qty=qty, price=price, order_no=order_no,
    )
    return OrderResult(order_no=order_no, fill_price=price, simulated=True)


async def _live_order(ticker: str, side: str, qty: int, price: int) -> OrderResult:
    token = await get_token()
    ord_dv = "2" if side == "buy" else "1"   # ⚠️ verify Kiwoom buy/sell codes

    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "authorization": f"{token.token_type} {token.access_token}",
        "api-id": "kt10000",   # ⚠️ verify TR code for limit order
    }
    payload = {
        "acnt_no": settings.active_account_number,
        "stk_cd": ticker,
        "ord_dv": ord_dv,
        "ord_qty": str(qty),
        "ord_pric": str(price),
    }

    log.info("order.live_submit", ticker=ticker, side=side, qty=qty, price=price)
    async with httpx.AsyncClient(base_url=settings.active_base_url) as client:
        resp = await client.post(_ORDER_PATH, headers=headers, json=payload)

    if resp.status_code != 200:
        raise BrokerError(f"Order failed [{resp.status_code}]: {resp.text}")

    data = resp.json()
    if data.get("return_code", -1) != 0:
        raise BrokerError(f"Order error: {data.get('return_msg')}")

    order_no = data.get("ord_no", "")
    log.info("order.live_accepted", ticker=ticker, order_no=order_no)
    return OrderResult(order_no=order_no, fill_price=price, simulated=False)
