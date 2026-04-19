"""RSI Mean Reversion: buy oversold (<30), sell overbought (>70)."""
from app.market.indicators import _rsi
from app.strategies.base import Signal

OVERSOLD   = 30
OVERBOUGHT = 70


class RSIMeanReversionStrategy:
    name = "rsi_reversion"

    async def generate_signal(
        self,
        ticker: str,
        closes: list[int],
        snapshot: dict,
        portfolio: dict,
    ) -> Signal | None:
        closes_f = [float(c) for c in closes]
        rsi = _rsi(closes_f, 14)
        if rsi is None:
            return None

        price = snapshot.get("price", 0)
        if price <= 0:
            return None

        cash = portfolio.get("cash", 0)
        qty = int(cash * 0.10) // price
        if qty < 1:
            return None

        if rsi < OVERSOLD:
            return Signal(
                ticker=ticker, side="buy", qty=qty, price=price,
                strategy=self.name,
                reasoning=f"RSI 과매도: {rsi:.1f} < {OVERSOLD} — 단기 반등 기대",
            )

        holdings = {h["ticker"]: h for h in portfolio.get("holdings", [])}
        pos = holdings.get(ticker)
        if rsi > OVERBOUGHT and pos:
            return Signal(
                ticker=ticker, side="sell", qty=pos["qty"], price=price,
                strategy=self.name,
                reasoning=f"RSI 과매수: {rsi:.1f} > {OVERBOUGHT} — 차익 실현",
            )

        return None
