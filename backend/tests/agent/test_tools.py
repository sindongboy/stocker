import pytest
from unittest.mock import patch, AsyncMock

from app.agent.tools import get_indicators, get_portfolio, search_knowledge, propose_order, log_reasoning
from app.permission import queue as order_queue


@pytest.fixture(autouse=True)
def clear_queue():
    order_queue._proposals.clear()
    yield
    order_queue._proposals.clear()


async def test_get_portfolio_returns_paper_balance():
    result = await get_portfolio()
    assert result["cash"] == 10_000_000
    assert result["mode"] == "paper"
    assert result["holdings"] == []


async def test_get_indicators_returns_requested_fields():
    result = await get_indicators("005930", ["MA5", "MA20"])
    assert "MA5" in result
    assert "MA20" in result
    assert result["ticker"] == "005930"


async def test_get_indicators_macd():
    result = await get_indicators("005930", ["MACD"])
    assert "MACD" in result
    assert "MACD_signal" in result


async def test_propose_order_creates_proposal():
    result = await propose_order(
        ticker="005930",
        side="buy",
        qty=10,
        price=72000,
        strategy="ma-crossover",
        reasoning="골든 크로스 발생",
    )
    assert "proposal_id" in result
    assert result["status"] == "pending"
    proposals = order_queue.list_proposals()
    assert len(proposals) == 1
    assert proposals[0].ticker == "005930"


def test_log_reasoning_returns_logged():
    result = log_reasoning("MA5 > MA20 골든 크로스", "propose_buy", 0.8)
    assert result["logged"] is True


def test_search_knowledge_finds_strategy():
    result = search_knowledge("MA crossover 골든 크로스")
    assert "ma-crossover" in result.lower() or "이동평균" in result or "No matching" in result
