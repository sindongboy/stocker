from dataclasses import dataclass
from pathlib import Path

import yaml

from app.portfolio.store import Portfolio

_PERMISSIONS_PATH = Path(__file__).parents[3] / "config" / "permissions.yaml"

_FALLBACK_T2_SINGLE = 500_000
_FALLBACK_T2_DAILY = 2_000_000


def _load_t2_limits() -> tuple[int, int]:
    """Return (max_single_order_krw, max_daily_krw) from permissions.yaml."""
    try:
        data = yaml.safe_load(_PERMISSIONS_PATH.read_text(encoding="utf-8"))
        t2 = data["tiers"]["T2"]
        return int(t2["max_single_order_krw"]), int(t2["max_daily_krw"])
    except Exception:
        return _FALLBACK_T2_SINGLE, _FALLBACK_T2_DAILY


CONCENTRATION_LIMIT = 0.20
MAX_POSITIONS = 10
POSITION_SIZE_PCT = 0.10

# Loaded once at import; T2 limits authoritative source is permissions.yaml
T2_SINGLE_LIMIT, T2_DAILY_LIMIT = _load_t2_limits()


@dataclass
class RiskResult:
    allowed: bool
    reason: str
    qty: int = 0


def check_buy(ticker: str, price: int, portfolio: Portfolio) -> RiskResult:
    if price <= 0:
        return RiskResult(False, "price is zero — possibly halted")

    if -portfolio.daily_realized_pnl >= T2_DAILY_LIMIT:
        return RiskResult(
            False,
            f"daily loss limit reached ({-portfolio.daily_realized_pnl:,}원 ≥ {T2_DAILY_LIMIT:,}원)",
        )

    if ticker not in portfolio.positions and len(portfolio.positions) >= MAX_POSITIONS:
        return RiskResult(False, f"max positions ({MAX_POSITIONS}) already open")

    budget = int(portfolio.cash * POSITION_SIZE_PCT)
    if budget < price:
        return RiskResult(False, f"budget ({budget:,}원) < price ({price:,}원)")

    qty = budget // price
    if qty < 1:
        return RiskResult(False, "qty < 1 after sizing")

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


def classify_tier(qty: int, price: int, triggers: list[str] | None = None) -> str:
    """Classify an order into T2/T3/T4 based on permissions.yaml limits."""
    if triggers and any(t in triggers for t in ("new_strategy", "after_hours")):
        return "T4"
    order_value = qty * price
    if order_value <= T2_SINGLE_LIMIT:
        return "T2"
    return "T3"
