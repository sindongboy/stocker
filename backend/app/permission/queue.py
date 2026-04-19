import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


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
    tier: str = "T1"
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))


_proposals: list[OrderProposal] = []


def push(proposal: OrderProposal) -> OrderProposal:
    _proposals.append(proposal)
    return proposal


def list_proposals(status: ProposalStatus | None = None) -> list[OrderProposal]:
    if status is not None:
        return [p for p in _proposals if p.status == status]
    return list(_proposals)


def get_proposal(proposal_id: str) -> OrderProposal | None:
    return next((p for p in _proposals if p.id == proposal_id), None)


def update_status(proposal_id: str, status: ProposalStatus) -> OrderProposal | None:
    proposal = get_proposal(proposal_id)
    if proposal:
        proposal.status = status
    return proposal
