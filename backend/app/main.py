from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.agent.router import router as agent_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.market.router import router as market_router, start_broadcaster, stop_broadcaster
from app.strategies.router import api_router as strategy_router

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    log.info(
        "startup",
        trading_mode=settings.trading_mode,
        permission_profile=settings.permission_profile,
    )
    await start_broadcaster()
    yield
    await stop_broadcaster()
    log.info("shutdown")


app = FastAPI(title="Stocker KR", version="0.3.0", lifespan=lifespan)

app.include_router(market_router)
app.include_router(agent_router)
app.include_router(strategy_router)


@app.get("/health")
async def health():
    return {"status": "ok", "trading_mode": settings.trading_mode}


@app.get("/api/v1/info")
async def info():
    return {
        "version": "0.3.0",
        "trading_mode": settings.trading_mode,
        "permission_profile": settings.permission_profile,
    }
