from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


class ProposalRow(SQLModel, table=True):
    __tablename__ = "proposals"

    id: str = Field(primary_key=True)
    ticker: str
    name: str
    side: str
    qty: int
    price: int
    strategy: str
    reasoning: str
    status: str = "pending"
    tier: str = "T3"
    created_at: datetime = Field(default_factory=_now)
    executed_at: Optional[datetime] = None
    fill_price: Optional[int] = None
    order_no: Optional[str] = None


class TradeRow(SQLModel, table=True):
    __tablename__ = "trades"

    id: str = Field(primary_key=True)
    proposal_id: str = Field(foreign_key="proposals.id")
    ticker: str
    name: str
    side: str
    qty: int
    fill_price: int
    realized_pnl: int = 0
    executed_at: datetime = Field(default_factory=_now)


class WatchlistEntry(SQLModel, table=True):
    __tablename__ = "watchlist"

    ticker: str = Field(primary_key=True)
    name: str
    market: str = "KOSPI"
    added_at: datetime = Field(default_factory=_now)


class StateKV(SQLModel, table=True):
    __tablename__ = "state_kv"

    key: str = Field(primary_key=True)
    value: str
    updated_at: datetime = Field(default_factory=_now)
