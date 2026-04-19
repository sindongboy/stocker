from dataclasses import dataclass

from app.portfolio.store import Portfolio

CONCENTRATION_LIMIT = 0.20   # single stock ≤ 20% of total portfolio value
MAX_POSITIONS = 10
DAILY_LOSS_LIMIT = 2_000_000  # T2 daily limit from permissions.yaml
POSITION_SIZE_PCT = 0.10      # allocate 10% of cash per trade


@dataclass
class RiskResult:
    allowed: bool
    reason: str
    qty: int = 0


def check_buy(ticker: str, price: int, portfolio: Portfolio) -> RiskResult:
    if price <= 0:
        return RiskResult(False, "price is zero — possibly halted")

    # Daily loss guard
    if -portfolio.daily_realized_pnl >= DAILY_LOSS_LIMIT:
        return RiskResult(
            False,
            f"daily loss limit reached ({-portfolio.daily_realized_pnl:,}원 ≥ {DAILY_LOSS_LIMIT:,}원)",
        )

    # Max open positions
    if ticker not in portfolio.positions and len(portfolio.positions) >= MAX_POSITIONS:
        return RiskResult(False, f"max positions ({MAX_POSITIONS}) already open")

    # Position sizing: 10% of current cash
    budget = int(portfolio.cash * POSITION_SIZE_PCT)
    if budget < price:
        return RiskResult(False, f"budget ({budget:,}원) < price ({price:,}원)")

    qty = budget // price
    if qty < 1:
        return RiskResult(False, "qty < 1 after sizing")

    # Concentration limit
    total = portfolio.total_value or 1
    existing_value = portfolio.positions[ticker].market_value if ticker in portfolio.positions else 0
    add_value = qty * price
    if (existing_value + add_value) / total > CONCENTRATION_LIMIT:
        max_add = int(CONCENTRATION_LIMIT * total) - existing_value
        qty = max(0, max_add // price)
        if qty < 1:
            return RiskResult(False, f"concentration limit ({CONCENTRATION_LIMIT*100:.0f}%): already at max")

    return RiskResult(True, "ok", qty)


def check_sell(ticker: str, portfolio: Portfolio) -> RiskResult:
    pos = portfolio.positions.get(ticker)
    if pos is None or pos.qty == 0:
        return RiskResult(False, f"no position in {ticker}")
    return RiskResult(True, "ok", pos.qty)
