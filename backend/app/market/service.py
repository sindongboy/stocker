"""
Selects data source based on TRADING_MODE:
  paper → SyntheticSource  (no real API calls)
  live  → KiwoomMarketSource
"""
from app.core.config import settings
from app.market.kiwoom import KiwoomMarketSource
from app.market.source import MarketSource
from app.market.synthetic import SyntheticSource, get_universe
from app.market.schemas import WatchlistItem

# Default watchlist — KOSPI 대형주
_DEFAULT_TICKERS = ["005930", "000660", "035420", "035720", "068270", "005380"]

_watchlist: list[str] = list(_DEFAULT_TICKERS)


def get_source() -> MarketSource:
    if settings.trading_mode == "live":
        return KiwoomMarketSource()
    return SyntheticSource()


def list_watchlist() -> list[WatchlistItem]:
    universe = get_universe()
    items = []
    for ticker in _watchlist:
        if ticker in universe:
            name, _ = universe[ticker]
            items.append(WatchlistItem(ticker=ticker, name=name, market="KOSPI"))
        else:
            items.append(WatchlistItem(ticker=ticker, name=ticker, market="KOSPI"))
    return items


def add_to_watchlist(ticker: str) -> bool:
    if ticker not in _watchlist:
        _watchlist.append(ticker)
        return True
    return False


def remove_from_watchlist(ticker: str) -> bool:
    if ticker in _watchlist:
        _watchlist.remove(ticker)
        return True
    return False


def get_watchlist_tickers() -> list[str]:
    return list(_watchlist)
