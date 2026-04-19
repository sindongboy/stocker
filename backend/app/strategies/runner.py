import structlog

from app.market import service as market_service
from app.permission import queue as order_queue
from app.permission.queue import OrderProposal, OrderSide
from app.portfolio import store as portfolio_store
from app.risk.engine import check_buy, check_sell, classify_tier
from app.strategies.ma_crossover import MACrossoverStrategy
from app.strategies.rsi_reversion import RSIMeanReversionStrategy

log = structlog.get_logger()

STRATEGIES = [MACrossoverStrategy(), RSIMeanReversionStrategy()]


async def scan_all(tickers: list[str]) -> list[dict]:
    src = market_service.get_source()
    portfolio = portfolio_store.get()
    portfolio_dict = portfolio_store.as_dict()

    results: list[dict] = []

    for ticker in tickers:
        try:
            candles  = await src.get_daily_candles(ticker, count=60)
            snapshot = await src.get_snapshot(ticker)
        except Exception as e:
            log.warning("strategy.scan.fetch_error", ticker=ticker, error=str(e))
            continue

        closes   = [c.close for c in candles]
        snap_dict = snapshot.model_dump(mode="json")

        for strategy in STRATEGIES:
            try:
                signal = await strategy.generate_signal(ticker, closes, snap_dict, portfolio_dict)
            except Exception as e:
                log.warning("strategy.signal.error", strategy=strategy.name, ticker=ticker, error=str(e))
                continue

            if signal is None:
                continue

            risk = check_buy(ticker, signal.price, portfolio) if signal.side == "buy" \
                   else check_sell(ticker, portfolio)

            if not risk.allowed:
                log.info("strategy.risk_blocked", strategy=strategy.name, ticker=ticker, reason=risk.reason)
                results.append({
                    "ticker": ticker, "strategy": strategy.name,
                    "blocked": True, "reason": risk.reason,
                })
                continue

            if risk.qty > 0:
                signal.qty = risk.qty

            watchlist = market_service.list_watchlist()
            name = next((i.name for i in watchlist if i.ticker == ticker), ticker)
            proposal = OrderProposal(
                ticker=ticker, name=name,
                side=OrderSide(signal.side),
                qty=signal.qty, price=signal.price,
                strategy=signal.strategy,
                reasoning=signal.reasoning,
                tier=classify_tier(signal.qty, signal.price),
            )
            order_queue.push(proposal)
            log.info(
                "strategy.proposed",
                ticker=ticker, strategy=strategy.name,
                side=signal.side, qty=signal.qty, price=signal.price,
            )
            results.append({
                "ticker": ticker, "strategy": strategy.name,
                "side": signal.side, "qty": signal.qty, "price": signal.price,
                "proposal_id": proposal.id, "blocked": False,
            })

    return results
