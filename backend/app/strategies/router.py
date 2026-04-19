from fastapi import APIRouter

from app.market import service as market_service
from app.portfolio import store as portfolio_store
from app.strategies import runner
from app.strategies.runner import STRATEGIES

api_router = APIRouter(prefix="/api/v1/strategies", tags=["strategies"])


@api_router.post("/scan")
async def scan_strategies():
    tickers = market_service.get_watchlist_tickers()
    results = await runner.scan_all(tickers)
    signals  = [r for r in results if not r.get("blocked")]
    blocked  = [r for r in results if r.get("blocked")]
    return {
        "scanned_tickers": len(tickers),
        "strategies": len(STRATEGIES),
        "signals": len(signals),
        "blocked": len(blocked),
        "results": results,
    }


@api_router.get("/list")
async def list_strategies():
    return [{"name": s.name} for s in STRATEGIES]


@api_router.get("/portfolio")
async def get_portfolio():
    return portfolio_store.as_dict()
