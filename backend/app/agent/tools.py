import json
from datetime import datetime, timezone
from pathlib import Path

import structlog

from app.market import service as market_service
from app.market.indicators import calculate as calc_indicators
from app.permission import queue as order_queue
from app.permission.queue import OrderProposal, OrderSide
from app.risk.engine import classify_tier

log = structlog.get_logger()

# knowledge/ 는 프로젝트 루트에 위치 — 이 파일 기준으로 4단계 위
KNOWLEDGE_DIR = Path(__file__).parents[3] / "knowledge"
TRADES_LOG = Path(__file__).parents[3] / "data" / "logs" / "trades.jsonl"


async def get_market_snapshot(ticker: str) -> dict:
    src = market_service.get_source()
    snap = await src.get_snapshot(ticker)
    return snap.model_dump(mode="json")


async def get_indicators(ticker: str, indicators: list[str]) -> dict:
    src = market_service.get_source()
    candles = await src.get_daily_candles(ticker, count=60)
    closes = [c.close for c in candles]
    result = calc_indicators(ticker, closes)

    output: dict = {"ticker": ticker}
    for ind in indicators:
        key = ind.upper()
        if key in ("MA5", "SMA5"):
            output["MA5"] = result.ma5
        elif key in ("MA20", "SMA20"):
            output["MA20"] = result.ma20
        elif key == "RSI14":
            output["RSI14"] = result.rsi14
        elif key == "MACD":
            output["MACD"] = result.macd
            output["MACD_signal"] = result.macd_signal
            output["MACD_hist"] = result.macd_hist
    return output


async def get_portfolio() -> dict:
    from app.portfolio import store as portfolio_store
    return portfolio_store.as_dict()


def search_knowledge(query: str) -> str:
    if not KNOWLEDGE_DIR.exists():
        return "Knowledge directory not found."
    results: list[str] = []
    for md_file in KNOWLEDGE_DIR.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        if any(word.lower() in content.lower() for word in query.split()):
            rel = md_file.relative_to(KNOWLEDGE_DIR)
            results.append(f"=== {rel} ===\n{content}")
    if not results:
        return "No matching knowledge found."
    return "\n\n".join(results[:3])


async def propose_order(
    ticker: str, side: str, qty: int, price: int, strategy: str, reasoning: str
) -> dict:
    items = market_service.list_watchlist()
    name = next((i.name for i in items if i.ticker == ticker), ticker)
    proposal = OrderProposal(
        ticker=ticker,
        name=name,
        side=OrderSide(side),
        qty=qty,
        price=price,
        strategy=strategy,
        reasoning=reasoning,
        tier=classify_tier(qty, price),
    )
    order_queue.push(proposal)
    log.info("agent.propose_order", ticker=ticker, side=side, qty=qty, price=price)
    return {"proposal_id": proposal.id, "status": "pending"}


def log_reasoning(summary: str, decision: str, confidence: float) -> dict:
    log.info("agent.reasoning", summary=summary, decision=decision, confidence=confidence)
    entry = {
        "event": "agent.reasoning",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "summary": summary,
        "decision": decision,
        "confidence": confidence,
    }
    TRADES_LOG.parent.mkdir(parents=True, exist_ok=True)
    with TRADES_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return {"logged": True}
