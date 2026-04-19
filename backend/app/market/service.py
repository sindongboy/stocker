"""
Selects data source based on TRADING_MODE:
  paper → SyntheticSource  (no real API calls)
  live  → KiwoomMarketSource
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlmodel import Session

from app.core.config import settings
from app.market.kiwoom import KiwoomMarketSource
from app.market.source import MarketSource
from app.market.synthetic import SyntheticSource, get_universe
from app.market.schemas import WatchlistItem

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


def add_to_watchlist(ticker: str, session: "Session | None" = None) -> bool:
    if ticker not in _watchlist:
        _watchlist.append(ticker)
        if session is not None:
            _persist_watchlist(session)
        return True
    return False


def remove_from_watchlist(ticker: str, session: "Session | None" = None) -> bool:
    if ticker in _watchlist:
        _watchlist.remove(ticker)
        if session is not None:
            _persist_watchlist(session)
        return True
    return False


def get_watchlist_tickers() -> list[str]:
    return list(_watchlist)


def init_watchlist_from_db(session: "Session") -> None:
    """Load watchlist from DB at startup; fall back to defaults if empty."""
    import sqlmodel
    from app.db.models import WatchlistEntry
    rows = session.exec(sqlmodel.select(WatchlistEntry).order_by(WatchlistEntry.added_at)).all()
    if rows:
        _watchlist.clear()
        _watchlist.extend(row.ticker for row in rows)


def _persist_watchlist(session: "Session") -> None:
    import sqlmodel
    from app.db.models import WatchlistEntry
    universe = get_universe()
    # delete entries no longer in watchlist
    existing = session.exec(sqlmodel.select(WatchlistEntry)).all()
    existing_tickers = {r.ticker for r in existing}
    current_set = set(_watchlist)
    for row in existing:
        if row.ticker not in current_set:
            session.delete(row)
    # add new entries
    for ticker in _watchlist:
        if ticker not in existing_tickers:
            name = universe[ticker][0] if ticker in universe else ticker
            session.add(WatchlistEntry(ticker=ticker, name=name))
    session.commit()
