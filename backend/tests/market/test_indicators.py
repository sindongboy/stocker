import pytest
from app.market.indicators import calculate, _sma, _ema, _rsi


def _prices(n: int, base: int = 100) -> list[int]:
    return [base + i for i in range(n)]


def test_sma_basic():
    assert _sma([1.0, 2.0, 3.0, 4.0, 5.0], 5) == 3.0


def test_sma_insufficient_data_returns_none():
    assert _sma([1.0, 2.0], 5) is None


def test_ema_basic():
    prices = [float(i) for i in range(1, 15)]
    result = _ema(prices, 5)
    assert result is not None
    assert result > 0


def test_rsi_overbought():
    # Steadily rising prices → RSI near 100
    prices = [float(100 + i) for i in range(30)]
    rsi = _rsi(prices)
    assert rsi is not None
    assert rsi > 70


def test_rsi_insufficient_data_returns_none():
    assert _rsi([1.0, 2.0, 3.0], 14) is None


def test_calculate_returns_indicators():
    closes = _prices(60, base=72000)
    ind = calculate("005930", closes)
    assert ind.ticker == "005930"
    assert ind.ma5 is not None
    assert ind.ma20 is not None
    assert ind.rsi14 is not None
    assert ind.macd is not None


def test_calculate_ma5_less_than_ma20_on_downtrend():
    # Descending prices: recent average (MA5) < long-term (MA20)
    closes = list(range(100_000, 100_000 - 60, -1))
    ind = calculate("005930", closes)
    assert ind.ma5 is not None
    assert ind.ma20 is not None
    assert ind.ma5 < ind.ma20


def test_calculate_ma5_greater_than_ma20_on_uptrend():
    closes = list(range(60_000, 60_000 + 60))
    ind = calculate("005930", closes)
    assert ind.ma5 is not None
    assert ind.ma20 is not None
    assert ind.ma5 > ind.ma20
