"""MA5/MA20 Golden-Cross / Dead-Cross strategy (see knowledge/strategies/ma-crossover.md)."""
from app.market.indicators import _sma
from app.strategies.base import Signal

MIN_CROSS_PCT = 0.1   # ignore noise below 0.1% cross width


class MACrossoverStrategy:
    name = "ma_crossover"

    async def generate_signal(
        self,
        ticker: str,
        closes: list[int],
        snapshot: dict,
        portfolio: dict,
    ) -> Signal | None:
        if len(closes) < 22:
            return None

        price = snapshot.get("price", 0)
        if price <= 0:
            return None

        closes_f = [float(c) for c in closes]
        ma5_now   = _sma(closes_f, 5)
        ma20_now  = _sma(closes_f, 20)
        ma5_prev  = _sma(closes_f[:-1], 5)
        ma20_prev = _sma(closes_f[:-1], 20)

        if None in (ma5_now, ma20_now, ma5_prev, ma20_prev):
            return None

        cash = portfolio.get("cash", 0)
        qty = int(cash * 0.10) // price
        if qty < 1:
            return None

        cross_pct = abs(ma5_now - ma20_now) / ma20_now * 100  # type: ignore[operator]

        # Golden cross: MA5 crosses above MA20
        if ma5_prev < ma20_prev and ma5_now > ma20_now:  # type: ignore[operator]
            if cross_pct < MIN_CROSS_PCT:
                return None
            return Signal(
                ticker=ticker, side="buy", qty=qty, price=price,
                strategy=self.name,
                reasoning=(
                    f"골든 크로스: MA5({ma5_now:.0f}) > MA20({ma20_now:.0f}), "
                    f"교차폭 {cross_pct:.2f}%"
                ),
            )

        # Dead cross: MA5 crosses below MA20
        if ma5_prev > ma20_prev and ma5_now < ma20_now:  # type: ignore[operator]
            holdings = {h["ticker"]: h for h in portfolio.get("holdings", [])}
            pos = holdings.get(ticker)
            sell_qty = pos["qty"] if pos else 1
            return Signal(
                ticker=ticker, side="sell", qty=sell_qty, price=price,
                strategy=self.name,
                reasoning=(
                    f"데드 크로스: MA5({ma5_now:.0f}) < MA20({ma20_now:.0f}), "
                    f"교차폭 {cross_pct:.2f}%"
                ),
            )

        return None
