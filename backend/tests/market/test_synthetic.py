from datetime import date

import pytest

from app.market.synthetic import SyntheticSource, daily_candles, snapshot, tick_all, get_universe


def test_snapshot_returns_valid_data():
    snap = snapshot("005930")
    assert snap.ticker == "005930"
    assert snap.name == "삼성전자"
    assert snap.price > 0
    assert snap.market == "KOSPI"


def test_snapshot_unknown_ticker_raises():
    with pytest.raises(KeyError):
        snapshot("999999")


def test_daily_candles_count():
    candles = daily_candles("005930", count=60)
    # Weekends are excluded — expect 40–60 candles for 60 calendar days
    assert 40 <= len(candles) <= 60


def test_daily_candles_ohlc_invariant():
    candles = daily_candles("005930", count=30)
    for c in candles:
        assert c.high >= c.open
        assert c.high >= c.close
        assert c.low <= c.open
        assert c.low <= c.close
        assert c.volume > 0


def test_daily_candles_dates_are_weekdays():
    candles = daily_candles("005930", count=60)
    for c in candles:
        assert c.date.weekday() < 5, f"{c.date} is a weekend"


def test_tick_all_changes_prices():
    import app.market.synthetic as syn
    before = dict(syn._live)
    tick_all()
    after = dict(syn._live)
    # At least some prices should have changed
    assert any(before[t] != after[t] for t in before)


async def test_synthetic_source_get_snapshot():
    src = SyntheticSource()
    snap = await src.get_snapshot("000660")
    assert snap.ticker == "000660"
    assert snap.name == "SK하이닉스"


async def test_synthetic_source_get_candles():
    src = SyntheticSource()
    candles = await src.get_daily_candles("035420", count=20)
    assert len(candles) > 0


def test_universe_has_default_tickers():
    universe = get_universe()
    for ticker in ["005930", "000660", "035420"]:
        assert ticker in universe
