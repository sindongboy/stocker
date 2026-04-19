from dataclasses import dataclass, field
from datetime import date

from app.core.config import settings


@dataclass
class Position:
    ticker: str
    name: str
    qty: int
    avg_price: int
    current_price: int = 0

    @property
    def market_value(self) -> int:
        return self.qty * (self.current_price or self.avg_price)

    @property
    def unrealized_pnl(self) -> int:
        if not self.current_price:
            return 0
        return (self.current_price - self.avg_price) * self.qty


@dataclass
class DayStats:
    date: date
    realized_pnl: int = 0


@dataclass
class Portfolio:
    cash: int = 10_000_000
    positions: dict[str, Position] = field(default_factory=dict)
    _day_stats: DayStats = field(default_factory=lambda: DayStats(date=date.today()))

    @property
    def day_stats(self) -> DayStats:
        today = date.today()
        if self._day_stats.date != today:
            self._day_stats = DayStats(date=today)
        return self._day_stats

    @property
    def total_market_value(self) -> int:
        return sum(p.market_value for p in self.positions.values())

    @property
    def total_value(self) -> int:
        return self.cash + self.total_market_value

    @property
    def daily_realized_pnl(self) -> int:
        return self.day_stats.realized_pnl

    def apply_fill(self, ticker: str, name: str, side: str, qty: int, price: int) -> None:
        if side == "buy":
            if ticker in self.positions:
                pos = self.positions[ticker]
                total_cost = pos.avg_price * pos.qty + price * qty
                pos.qty += qty
                pos.avg_price = total_cost // pos.qty
            else:
                self.positions[ticker] = Position(ticker=ticker, name=name, qty=qty, avg_price=price)
            self.cash -= price * qty
        elif side == "sell":
            pos = self.positions.get(ticker)
            if pos and pos.qty >= qty:
                pnl = (price - pos.avg_price) * qty
                self.day_stats.realized_pnl += pnl
                pos.qty -= qty
                self.cash += price * qty
                if pos.qty == 0:
                    del self.positions[ticker]

    def update_prices(self, prices: dict[str, int]) -> None:
        for ticker, price in prices.items():
            if ticker in self.positions:
                self.positions[ticker].current_price = price


_portfolio = Portfolio()


def get() -> Portfolio:
    return _portfolio


def as_dict() -> dict:
    p = _portfolio
    return {
        "cash": p.cash,
        "total_value": p.total_value,
        "total_market_value": p.total_market_value,
        "daily_realized_pnl": p.daily_realized_pnl,
        "holdings": [
            {
                "ticker": pos.ticker,
                "name": pos.name,
                "qty": pos.qty,
                "avg_price": pos.avg_price,
                "current_price": pos.current_price,
                "market_value": pos.market_value,
                "unrealized_pnl": pos.unrealized_pnl,
            }
            for pos in p.positions.values()
        ],
        "mode": settings.trading_mode,
    }
