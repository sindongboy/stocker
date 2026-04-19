from datetime import date, datetime
from pydantic import BaseModel


class Snapshot(BaseModel):
    ticker: str
    name: str
    price: int          # KRW — always integer
    change: int         # vs previous close
    change_pct: float
    volume: int
    market: str         # KOSPI | KOSDAQ
    timestamp: datetime


class Candle(BaseModel):
    date: date
    open: int
    high: int
    low: int
    close: int
    volume: int


class WatchlistItem(BaseModel):
    ticker: str
    name: str
    market: str
