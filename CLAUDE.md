# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project in One Line

Korean stock market (KOSPI/KOSDAQ spot + ETF/ETN) AI trading agent. Gemini reasons over market state → proposes orders → user approves → Kiwoom REST API executes. **No futures/options, no overseas stocks (v1).**

---

## Commands

```bash
# Setup (one-time)
make setup           # installs backend (uv) + frontend (pnpm) + copies .envrc.example → .envrc.local

# Development
make dev             # launches tmux session: backend / frontend / redis in split panes
make paper           # backend only in TRADING_MODE=paper

# Backend
uv run pytest                          # all tests
uv run pytest backend/tests/path/test_file.py::test_name   # single test
uv run python -m app.main              # backend standalone

# Frontend
cd frontend && pnpm dev                # Next.js dev server
cd frontend && pnpm test               # frontend tests
cd frontend && pnpm build              # production build

# Infrastructure
docker-compose up -d                   # Redis (+ optional Postgres)
```

> Until M1 scaffolding is done, most commands above don't exist yet. Add real paths here as they're created.

---

## Architecture

### Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.12 + FastAPI, `uv` packaging |
| Frontend | Next.js 14 + TypeScript + Tailwind, `pnpm` |
| DB | SQLite dev / PostgreSQL prod opt-in |
| Cache/Queue | Redis |
| Runtime LLM | Google Gemini API (`google-genai` SDK — **not** `google-generativeai`) |
| Broker | Kiwoom REST API (**not** OCX/Open API+) |

### Key Directories

```
backend/app/
├── agent/          # Gemini reasoning loop: planner → tools → executor → memory
├── broker/         # Kiwoom REST + WebSocket wrapper
├── strategies/     # Strategy implementations (logic only; knowledge stays in /knowledge/)
├── market/         # Price feeds, indicators, orderbook
├── risk/           # Position sizing, limit checks
├── permission/     # Approval workflow, Tier state machine
└── core/           # Config, logging (structlog+JSON), exceptions

knowledge/          # Markdown cards read by the agent at runtime (NOT hardcoded in code)
├── strategies/     # Strategy cards
├── market-rules/   # KRX rules (trading hours, price limits, tick sizes)
├── indicators/     # Indicator definitions
└── playbooks/      # Market regime playbooks

config/
└── permissions.yaml  # Tier limits declared here, not in code
```

### Agent Loop (Perception → Analysis → Decision → Action)

The agent is driven by Gemini function calling. Tools exposed to Gemini:

| Tool | Purpose |
|---|---|
| `get_market_snapshot(ticker)` | Price, orderbook, volume, daily candle |
| `get_indicators(ticker, set)` | RSI, MACD, moving averages |
| `get_portfolio()` | Holdings, cash, PnL |
| `get_news(ticker, lookback_hours)` | News/disclosure |
| `get_global_context()` | US indices, ETF, sector via Polygon/Finnhub |
| `search_knowledge(query)` | `/knowledge/` lookup |
| `propose_order(...)` | Pushes to approval queue (T1/T3/T4) |
| `place_order(...)` | Direct execute only within T2 limits |
| `log_reasoning(...)` | **Mandatory last call.** No decision is valid without it. |

### Approval Tier System

Orders flow through `pending → approved/rejected → executed/failed`.

| Tier | Scope | Default |
|---|---|---|
| T0 View | Read-only | Auto |
| T1 Suggest | Proposal only | Auto |
| T2 Small | Single order ≤ limitA AND daily ≤ limitB | Auto if pre-approved |
| T3 Normal | Above T2 limits | Manual per order |
| T4 Sensitive | New strategy / leverage / after-hours | Manual + 2-step confirm |

Limits are declared in `config/permissions.yaml`. Live mode is toggled **in UI only** — not via CLI flags or code.

### Data Sources

- **Kiwoom REST API** — all Korean price/order/position data (primary)
- **Polygon.io** — US indices, ETF, sector context only
- **Finnhub** — global comps, FX, commodities context only

Polygon/Finnhub are **context**, not substitutes for Kiwoom data on Korean stocks.

---

## Rules Claude Must Follow

### Hard Rules

- respond only in English unless I ask you to speak in other language
- Never add a new dependency without user confirmation. Do not run `uv add` or `pnpm add` directly.
- Never guess Kiwoom REST API endpoints or parameters — check `/knowledge/kiwoom-api/` or ask for official docs.
- Never reference OCX-based "키움 Open API+" code or docs. This project uses REST only.
- Never write placeholder/stub/TODO code for Phase 2 data sources (DART, BOK ECOS, Naver News). Add them only when needed.
- Never run `TRADING_MODE=live` code paths in tests.
- Market order type is blocked by default. Limit orders only. Exceptions require user selection in UI.

### Code Style

- All Python external boundaries use Pydantic v2 schemas.
- Custom exceptions: `BrokerError`, `PermissionDenied`, `StrategyError`, `RiskLimitBreached`.
- Trade logs: structlog JSON → `data/logs/trades.jsonl`.
- Tests: broker layer uses VCR fixtures; strategies use synthetic price data; agent layer uses tool-call sequence snapshots.

### Language in Responses

- **Respond in English by default.** Korean input from user = token economy, not a request for Korean output.
- Korean domain terms stay Korean even in English prose: 종목, 잔고, 체결, 상한가, 동시호가, 호가, 공시.

---

## Environment

Copy `.envrc.example` to `.envrc.local`, fill in keys, then `direnv allow .`.

Key vars: `KIWOOM_APP_KEY/SECRET/ACCOUNT_NUMBER/HTS_ID`, `GEMINI_API_KEY`, `POLYGON_API_KEY`, `FINNHUB_API_KEY`, `TRADING_MODE=paper`, `PERMISSION_PROFILE=strict`.

Mock (모의투자) uses separate keys: `KIWOOM_MOCK_APP_KEY/SECRET/ACCOUNT_NUMBER`, base URL `https://mockapi.kiwoom.com`.

---

## Milestones

| # | Goal | Status |
|---|---|---|
| M1 | Infra scaffolding — `make setup`, FastAPI hello, Next.js shell, Kiwoom token issuance | ✅ |
| M2 | Market data + dashboard — watchlist, realtime price, daily chart | ✅ |
| M3 | Paper order execution — E2E limit buy/sell on mock account | ⏸ (deferred) |
| M4 | Simple strategy agent — MA crossover card + Gemini proposal | ✅ |
| M5 | Approval workflow UI — queue, tier policy, execution log | ✅ |
| M6 | Multi-strategy + risk engine — sizing, correlation, limits | 🔲 |
| M7 | Backtest harness | 🔲 |
| M8 | Live mode unlock checklist | 🔲 |
