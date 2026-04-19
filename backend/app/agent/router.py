import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agent import runner
from app.core.config import settings
from app.permission import queue as order_queue
from app.permission.queue import ProposalStatus

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])

TRADES_LOG = Path(__file__).parents[3] / "data" / "logs" / "trades.jsonl"


class RunRequest(BaseModel):
    tickers: list[str]


@router.post("/run")
async def run_agent(req: RunRequest):
    if not settings.gemini_api_key:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY not configured")
    if not req.tickers:
        raise HTTPException(status_code=400, detail="tickers must not be empty")
    return await runner.run_cycle(req.tickers)


@router.get("/proposals")
async def list_proposals(status: str | None = None):
    try:
        ps = ProposalStatus(status) if status else None
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    return [
        {
            "id": p.id,
            "ticker": p.ticker,
            "name": p.name,
            "side": p.side,
            "qty": p.qty,
            "price": p.price,
            "strategy": p.strategy,
            "reasoning": p.reasoning,
            "status": p.status,
            "tier": p.tier,
            "created_at": p.created_at.isoformat(),
        }
        for p in order_queue.list_proposals(ps)
    ]


@router.get("/reasoning")
async def list_reasoning(limit: int = 50):
    if not TRADES_LOG.exists():
        return []
    entries: list[dict] = []
    with TRADES_LOG.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries[-limit:][::-1]


@router.patch("/proposals/{proposal_id}")
async def update_proposal(proposal_id: str, status: str):
    try:
        ps = ProposalStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    proposal = order_queue.update_status(proposal_id, ps)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return {"id": proposal.id, "status": proposal.status}
