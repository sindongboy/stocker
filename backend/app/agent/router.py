import json
import uuid
from pathlib import Path

import sqlmodel
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agent import runner
from app.broker import kiwoom_order
from app.core.config import settings
from app.core.exceptions import BrokerError
from app.db.engine import get_session
from app.db.models import TradeRow
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
            "fill_price": p.fill_price,
            "order_no": p.order_no,
            "executed_at": p.executed_at.isoformat() if p.executed_at else None,
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

    proposal = order_queue.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if ps == ProposalStatus.approved and proposal.fill_price is None:
        # Execute the order
        try:
            result = await kiwoom_order.place_limit_order(
                ticker=proposal.ticker,
                side=proposal.side.value,
                qty=proposal.qty,
                price=proposal.price,
            )
        except BrokerError as e:
            raise HTTPException(status_code=502, detail=str(e))

        with get_session() as session:
            order_queue.update_status(proposal_id, ps, session)
            order_queue.record_execution(
                proposal_id,
                fill_price=result.fill_price,
                order_no=result.order_no,
                session=session,
            )
            # Apply fill to in-memory portfolio
            from app.portfolio import store as portfolio_store
            portfolio_store.get().apply_fill(
                ticker=proposal.ticker,
                name=proposal.name,
                side=proposal.side.value,
                qty=proposal.qty,
                price=result.fill_price,
            )
            # Record trade in DB
            pos = portfolio_store.get().positions.get(proposal.ticker)
            realized_pnl = 0
            if proposal.side.value == "sell" and pos is None:
                # position was closed — pnl was already applied in apply_fill
                realized_pnl = portfolio_store.get().daily_realized_pnl

            trade = TradeRow(
                id=str(uuid.uuid4()),
                proposal_id=proposal_id,
                ticker=proposal.ticker,
                name=proposal.name,
                side=proposal.side.value,
                qty=proposal.qty,
                fill_price=result.fill_price,
                realized_pnl=realized_pnl,
            )
            session.add(trade)
            session.commit()
    else:
        with get_session() as session:
            order_queue.update_status(proposal_id, ps, session)

    updated = order_queue.get_proposal(proposal_id)
    return {
        "id": updated.id,
        "status": updated.status,
        "fill_price": updated.fill_price,
        "order_no": updated.order_no,
        "executed_at": updated.executed_at.isoformat() if updated.executed_at else None,
    }


@router.get("/trades")
async def list_trades(limit: int = 100):
    with get_session() as session:
        rows = session.exec(
            sqlmodel.select(TradeRow).order_by(TradeRow.executed_at.desc()).limit(limit)
        ).all()
    return [
        {
            "id": r.id,
            "proposal_id": r.proposal_id,
            "ticker": r.ticker,
            "name": r.name,
            "side": r.side,
            "qty": r.qty,
            "fill_price": r.fill_price,
            "realized_pnl": r.realized_pnl,
            "executed_at": r.executed_at.isoformat(),
        }
        for r in rows
    ]
