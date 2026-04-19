import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlmodel import Session


class OrderSide(str, Enum):
    buy = "buy"
    sell = "sell"


class ProposalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


@dataclass
class OrderProposal:
    ticker: str
    name: str
    side: OrderSide
    qty: int
    price: int
    strategy: str
    reasoning: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: ProposalStatus = ProposalStatus.pending
    tier: str = "T3"
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    executed_at: datetime | None = None
    fill_price: int | None = None
    order_no: str | None = None


_proposals: list[OrderProposal] = []


# ── DB helpers (no-op when session is None, e.g. in unit tests) ───────────────

def _upsert_db(proposal: OrderProposal, session: "Session | None" = None) -> None:
    if session is None:
        return
    from app.db.models import ProposalRow
    row = session.get(ProposalRow, proposal.id)
    if row is None:
        row = ProposalRow(id=proposal.id)
        session.add(row)
    row.ticker = proposal.ticker
    row.name = proposal.name
    row.side = proposal.side.value
    row.qty = proposal.qty
    row.price = proposal.price
    row.strategy = proposal.strategy
    row.reasoning = proposal.reasoning
    row.status = proposal.status.value
    row.tier = proposal.tier
    row.created_at = proposal.created_at
    row.executed_at = proposal.executed_at
    row.fill_price = proposal.fill_price
    row.order_no = proposal.order_no
    session.commit()


def init_from_db(session: "Session") -> None:
    """Reload proposals from DB into memory at startup."""
    from app.db.models import ProposalRow
    _proposals.clear()
    rows = session.exec(__import__("sqlmodel").select(ProposalRow).order_by(ProposalRow.created_at)).all()
    for row in rows:
        _proposals.append(OrderProposal(
            id=row.id,
            ticker=row.ticker,
            name=row.name,
            side=OrderSide(row.side),
            qty=row.qty,
            price=row.price,
            strategy=row.strategy,
            reasoning=row.reasoning,
            status=ProposalStatus(row.status),
            tier=row.tier,
            created_at=row.created_at,
            executed_at=row.executed_at,
            fill_price=row.fill_price,
            order_no=row.order_no,
        ))


# ── Public API ─────────────────────────────────────────────────────────────────

def push(proposal: OrderProposal, session: "Session | None" = None) -> OrderProposal:
    _proposals.append(proposal)
    _upsert_db(proposal, session)
    return proposal


def list_proposals(status: ProposalStatus | None = None) -> list[OrderProposal]:
    if status is not None:
        return [p for p in _proposals if p.status == status]
    return list(_proposals)


def get_proposal(proposal_id: str) -> OrderProposal | None:
    return next((p for p in _proposals if p.id == proposal_id), None)


def update_status(
    proposal_id: str,
    status: ProposalStatus,
    session: "Session | None" = None,
) -> OrderProposal | None:
    proposal = get_proposal(proposal_id)
    if proposal:
        proposal.status = status
        _upsert_db(proposal, session)
    return proposal


def record_execution(
    proposal_id: str,
    fill_price: int,
    order_no: str | None = None,
    session: "Session | None" = None,
) -> OrderProposal | None:
    proposal = get_proposal(proposal_id)
    if proposal:
        proposal.fill_price = fill_price
        proposal.order_no = order_no
        proposal.executed_at = datetime.now(tz=timezone.utc)
        _upsert_db(proposal, session)
    return proposal
