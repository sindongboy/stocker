from dataclasses import dataclass
from typing import Sequence


@dataclass
class Indicators:
    ticker: str
    ma5: float | None
    ma20: float | None
    rsi14: float | None
    macd: float | None
    macd_signal: float | None
    macd_hist: float | None


def _sma(prices: Sequence[float], period: int) -> float | None:
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def _ema(prices: Sequence[float], period: int) -> float | None:
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for p in prices[period:]:
        ema = p * k + ema * (1 - k)
    return ema


def _rsi(prices: Sequence[float], period: int = 14) -> float | None:
    if len(prices) < period + 1:
        return None
    changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    recent = changes[-period:]
    avg_gain = sum(max(0.0, c) for c in recent) / period
    avg_loss = sum(max(0.0, -c) for c in recent) / period
    if avg_loss == 0:
        return 100.0
    return round(100 - (100 / (1 + avg_gain / avg_loss)), 2)


def _macd(prices: Sequence[float]) -> tuple[float, float, float] | None:
    """Returns (macd_line, signal, histogram). Needs ≥ 35 data points."""
    if len(prices) < 35:
        return None
    fast = _ema(prices, 12)
    slow = _ema(prices, 26)
    if fast is None or slow is None:
        return None
    macd_line = fast - slow

    # Build 9-period signal from recent MACD values
    macd_series: list[float] = []
    for end in range(26, len(prices) + 1):
        f = _ema(prices[:end], 12)
        s = _ema(prices[:end], 26)
        if f is not None and s is not None:
            macd_series.append(f - s)

    signal = _ema(macd_series, 9)
    if signal is None:
        return None
    return macd_line, signal, macd_line - signal


def calculate(ticker: str, closes: list[int]) -> Indicators:
    prices = [float(p) for p in closes]
    macd_result = _macd(prices)
    return Indicators(
        ticker=ticker,
        ma5=round(_sma(prices, 5), 2) if _sma(prices, 5) else None,
        ma20=round(_sma(prices, 20), 2) if _sma(prices, 20) else None,
        rsi14=_rsi(prices),
        macd=round(macd_result[0], 2) if macd_result else None,
        macd_signal=round(macd_result[1], 2) if macd_result else None,
        macd_hist=round(macd_result[2], 2) if macd_result else None,
    )
