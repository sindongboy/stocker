import asyncio
import random
from datetime import date, datetime, timedelta, timezone
from typing import AsyncIterator

from app.market.schemas import Candle, Snapshot

# Representative KOSPI 종목 (ticker → (name, base_price))
_UNIVERSE: dict[str, tuple[str, int]] = {
    "005930": ("삼성전자", 72000),
    "000660": ("SK하이닉스", 185000),
    "035420": ("NAVER", 210000),
    "035720": ("카카오", 58000),
    "068270": ("셀트리온", 165000),
    "005380": ("현대차", 245000),
    "051910": ("LG화학", 415000),
    "006400": ("삼성SDI", 320000),
    "207940": ("삼성바이오로직스", 890000),
    "028260": ("삼성물산", 127000),
}

_DAILY_VOL = 0.018      # ~1.8% daily volatility (KRX typical)
_INTRA_VOL = 0.0015     # per-second tick volatility

# In-memory live prices (initialised from base prices, drift with each tick)
_live: dict[str, int] = {t: p for t, (_, p) in _UNIVERSE.items()}
_prev_close: dict[str, int] = dict(_live)


def _step(price: int, vol: float) -> int:
    delta = int(price * random.gauss(0, vol))
    return max(100, price + delta)


def _round_to_tick(price: int) -> int:
    """KRX 호가 단위 (simplified — full table lives in knowledge/)."""
    if price < 2_000:       return max(1, round(price / 1) * 1)
    if price < 5_000:       return max(5, round(price / 5) * 5)
    if price < 20_000:      return max(10, round(price / 10) * 10)
    if price < 50_000:      return max(50, round(price / 50) * 50)
    if price < 200_000:     return max(100, round(price / 100) * 100)
    if price < 500_000:     return max(500, round(price / 500) * 500)
    return max(1000, round(price / 1000) * 1000)


def _ticker_info(ticker: str) -> tuple[str, str]:
    """Return (name, market). Falls back gracefully for unknown tickers."""
    if ticker in _UNIVERSE:
        name, _ = _UNIVERSE[ticker]
        return name, "KOSPI"
    return ticker, "KOSPI"


def get_universe() -> dict[str, tuple[str, int]]:
    return _UNIVERSE


def snapshot(ticker: str) -> Snapshot:
    if ticker not in _live:
        raise KeyError(f"Unknown ticker: {ticker}")
    price = _live[ticker]
    prev = _prev_close[ticker]
    name, market = _ticker_info(ticker)
    return Snapshot(
        ticker=ticker,
        name=name,
        price=price,
        change=price - prev,
        change_pct=round((price - prev) / prev * 100, 2),
        volume=random.randint(50_000, 3_000_000),
        market=market,
        timestamp=datetime.now(tz=timezone.utc),
    )


def tick_all() -> None:
    """Advance all live prices by one random step."""
    for ticker in _live:
        _live[ticker] = _round_to_tick(_step(_live[ticker], _INTRA_VOL))


def daily_candles(ticker: str, count: int = 60) -> list[Candle]:
    if ticker not in _UNIVERSE:
        raise KeyError(f"Unknown ticker: {ticker}")
    _, base = _UNIVERSE[ticker]

    # Build closing prices backwards from today
    closes = [base]
    for _ in range(count):
        closes.append(_step(closes[-1], _DAILY_VOL))
    closes.reverse()

    candles: list[Candle] = []
    today = date.today()
    close_iter = iter(closes)
    prev_close = next(close_iter)

    for i in range(count):
        day = today - timedelta(days=count - i)
        if day.weekday() >= 5:      # 토/일 제외
            continue
        close = _round_to_tick(next(close_iter, prev_close))
        open_ = _round_to_tick(_step(prev_close, _DAILY_VOL * 0.5))
        high = max(open_, close) + random.randint(0, close // 200)
        low  = min(open_, close) - random.randint(0, close // 200)
        high = _round_to_tick(high)
        low  = _round_to_tick(max(100, low))
        candles.append(Candle(
            date=day, open=open_, high=high, low=low, close=close,
            volume=random.randint(100_000, 8_000_000),
        ))
        prev_close = close

    return candles


def _aggregate(candles: list[Candle], key_fn) -> list[Candle]:
    """Aggregate daily candles into weekly/monthly OHLCV."""
    groups: dict[str, list[Candle]] = {}
    for c in candles:
        k = key_fn(c.date)
        groups.setdefault(k, []).append(c)
    result = []
    for k in sorted(groups):
        grp = groups[k]
        result.append(Candle(
            date=grp[0].date,
            open=grp[0].open,
            high=max(c.high for c in grp),
            low=min(c.low for c in grp),
            close=grp[-1].close,
            volume=sum(c.volume for c in grp),
        ))
    return result


class SyntheticSource:
    async def get_snapshot(self, ticker: str) -> Snapshot:
        return snapshot(ticker)

    async def get_daily_candles(self, ticker: str, count: int = 60) -> list[Candle]:
        return daily_candles(ticker, count)

    async def get_candles(self, ticker: str, period: str = "D", count: int = 60) -> list[Candle]:
        if period == "W":
            raw = daily_candles(ticker, count * 7)
            return _aggregate(raw, lambda d: f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}")[-count:]
        if period == "M":
            raw = daily_candles(ticker, count * 30)
            return _aggregate(raw, lambda d: f"{d.year}-{d.month:02d}")[-count:]
        return daily_candles(ticker, count)

    async def stream_snapshots(self, tickers: list[str]) -> AsyncIterator[dict[str, Snapshot]]:
        while True:
            tick_all()
            yield {t: snapshot(t) for t in tickers if t in _live}
            await asyncio.sleep(1)
