# MoneyLogix Strategy Builder

> An AI-native options strategy lifecycle platform for Indian index options.
> Users construct multi-leg strategies. The system analyzes, monitors, stress-tests,
> and explains them in real time — without ever making investment recommendations.

---

## How to Run (3 Terminals)

### Prerequisites
- Python 3.11 installed
- Node.js 18+ installed
- Git installed

---

### Terminal 1 — Backend API

```bash
cd moneylogix-strategy-builder\backend
python -m venv venv
venv\Scripts\activate
pip install -r ..\requirements.txt
uvicorn main:app --reload --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     MoneyLogix Strategy Builder API started
```

Keep this terminal open. Backend runs on **http://localhost:8000**

---

### Terminal 2 — Frontend

```bash
cd moneylogix-strategy-builder\frontend
npm install
npm run dev
```

**Expected output:**
```
  VITE v5.x.x  ready in 500ms
  ➜  Local:   http://localhost:5173/
```

Keep this terminal open. Open **http://localhost:5173** in your browser.

---

### Terminal 3 — Tests (run once to verify everything works)

```bash
cd moneylogix-strategy-builder\backend
venv\Scripts\activate
pytest ..\tests\ -v
```

**Expected output:** All tests green. Fix any failures before the demo.

---

### Verify Everything is Connected

With both Terminal 1 and Terminal 2 running:

1. Open http://localhost:5173 — dark UI should load
2. Open http://localhost:8000/health — should return `{"status":"ok"}`
3. Add legs in the UI, click Analyze — metrics should appear

If metrics don't appear, check Terminal 1 for errors.

---

## What Each Terminal Does

| Terminal | What runs | Port | Kill with |
|----------|-----------|------|-----------|
| Terminal 1 | FastAPI backend — all math, data, AI | 8000 | Ctrl+C |
| Terminal 2 | React frontend — the UI you interact with | 5173 | Ctrl+C |
| Terminal 3 | Tests — run once, not kept open | — | Finishes automatically |

---

## Switching AI Provider

By default the app uses **MockProvider** — no API key needed, works offline.

To switch to Claude:

1. Create a `.env` file in the `backend/` folder:
```
AI_PROVIDER=claude
ANTHROPIC_API_KEY=your_key_here
```

2. Restart Terminal 1 (Ctrl+C then run uvicorn again)

To switch back to mock: set `AI_PROVIDER=mock` or delete the `.env` file.

---

## If NSE Data Fails

The app never crashes due to missing data. It falls back automatically:

```
Live NSE → Cache (60s) → SQLite Snapshot → Demo Mock Data
```

The banner at the top of the page shows which data source is active:
- Green "● Live Data" — NSE is working
- Blue "● Cached Data" — using recent cache
- Yellow "⚠ Snapshot Data" — using last saved state
- Orange "Demo Mode" — using hardcoded sample data

Full functionality works in all four modes.

---

## Project Structure

```
moneylogix-strategy-builder/
├── backend/
│   ├── main.py                  ← FastAPI app, all routes, WebSocket
│   ├── config.py                ← All settings, read from .env
│   ├── models.py                ← Pydantic request/response models
│   ├── database.py              ← SQLite setup and CRUD
│   ├── data/
│   │   ├── mock_data.py         ← Hardcoded Nifty/BankNifty chain (Tier 4)
│   │   ├── cache.py             ← In-memory TTL cache (Tier 2)
│   │   ├── nse_fetcher.py       ← Live NSE option chain (Tier 1)
│   │   ├── historical.py        ← yfinance IV history
│   │   └── fallback.py          ← 4-tier cascade orchestrator
│   ├── quant/
│   │   ├── blackscholes.py      ← BS pricing, delta, theta, gamma, vega
│   │   ├── portfolio_greeks.py  ← Aggregate per-leg Greeks
│   │   ├── payoff.py            ← Payoff curve at expiry
│   │   ├── iv_rank.py           ← IV rank and regime classification
│   │   ├── expected_move.py     ← Market-implied expected move
│   │   ├── probability.py       ← Probability of profit
│   │   ├── margin.py            ← Simplified SPAN margin estimate
│   │   ├── liquidity.py         ← Bid-ask and OI liquidity score
│   │   └── stress_test.py       ← 5×7 scenario matrix
│   ├── engine/
│   │   ├── strategy_builder.py  ← Main orchestrator (calls all quant/)
│   │   ├── assumption_checker.py← 4-assumption check per strategy type
│   │   ├── health_monitor.py    ← Diffs current vs entry state
│   │   ├── adjustment_simulator.py ← Before/after leg change comparison
│   │   └── snapshot.py          ← Strategy state persistence
│   ├── ai/
│   │   ├── base_provider.py     ← Abstract AI interface
│   │   ├── mock_provider.py     ← Template-based, no API key needed
│   │   ├── claude_provider.py   ← Claude API (set AI_PROVIDER=claude)
│   │   ├── explainer.py         ← Lifecycle change explanation
│   │   └── copilot.py           ← Inline leg-edit hints
│   └── utils/
│       ├── logger.py            ← Structured JSON logging
│       └── validators.py        ← Input validation
├── frontend/
│   └── src/
│       ├── types/strategy.ts    ← All TypeScript interfaces
│       ├── api/client.ts        ← Typed API functions
│       ├── hooks/
│       │   ├── useStrategy.ts   ← Strategy state (useReducer)
│       │   ├── useWebSocket.ts  ← Health monitor WebSocket
│       │   └── useOptionChain.ts← Option chain data
│       ├── utils/formatters.ts  ← formatINR, formatIV, formatDelta
│       ├── components/
│       │   ├── LegBuilder/      ← Leg construction UI + copilot hints
│       │   ├── PayoffChart/     ← ECharts payoff diagram
│       │   ├── MetricsPanel/    ← Greeks + risk metrics display
│       │   ├── AssumptionDashboard/ ← 4 assumption check cards
│       │   ├── StressTest/      ← Scenario heatmap (5×7 grid)
│       │   ├── HealthMonitor/   ← WebSocket health + AI explanation
│       │   ├── AIExplainer/     ← Explanation panel
│       │   └── DataModeBanner/  ← Live/Cache/Demo indicator
│       └── pages/
│           ├── StrategyWorkspace.tsx ← Main page
│           └── AdjustmentView.tsx    ← Before/after comparison
├── tests/
│   ├── test_blackscholes.py     ← Math verification tests
│   ├── test_payoff.py
│   ├── test_portfolio_greeks.py
│   ├── test_assumption_checker.py
│   ├── test_stress_test.py
│   └── test_fallback.py
├── requirements.txt
└── .env.example
```

---

## API Endpoints Reference

| Method | Endpoint | What it does |
|--------|----------|--------------|
| GET | /health | Verify API is running |
| GET | /option-chain/{symbol} | Fetch Nifty/BankNifty chain |
| POST | /strategy/analyze | Compute all metrics for legs |
| POST | /strategy/payoff | Payoff curve only (faster) |
| POST | /strategy/assumptions | Check 4 strategy assumptions |
| POST | /strategy/stress-test | 35-scenario heatmap |
| POST | /strategy/save | Save strategy for monitoring |
| GET | /strategy/{id}/history | Health event log |
| POST | /adjustment/simulate | Before/after comparison |
| POST | /copilot/hint | Inline leg-edit hint |
| POST | /explain | Lifecycle change explanation |
| WS | /ws/health/{id} | Real-time health monitor |

Full interactive docs at **http://localhost:8000/docs** (auto-generated by FastAPI)

---

## Common Issues and Fixes

**Backend won't start:**
```bash
# Make sure venv is activated
venv\Scripts\activate
# Make sure you're in the backend folder
cd backend
# Try reinstalling
pip install -r ..\requirements.txt
```

**Frontend shows blank page:**
```bash
# Check browser console for errors (F12)
# Make sure backend is running on port 8000
# Check that CORS is allowing http://localhost:5173
```

**"Analysis failed" in UI:**
- Check Terminal 1 for Python errors
- Verify http://localhost:8000/health returns 200
- Check the DataMode banner — if it shows Demo Mode, data is working, the issue is in computation

**WebSocket not connecting:**
- Make sure strategy is saved first (click "Save & Monitor")
- Check browser console — WebSocket URL must be `ws://` not `http://`
- Check Terminal 1 for WebSocket errors

**Tests failing:**
```bash
# Run just the failing test file with verbose output
pytest tests/test_blackscholes.py -v -s
# The -s flag shows print statements and logging
```

---

## Architecture in One Paragraph

The quant engine (backend/quant/) computes all numbers using Black-Scholes:
Greeks, payoff curves, IV rank, expected move, margin estimates, and stress
scenarios. The lifecycle engine (backend/engine/) orchestrates these into
complete strategy analysis, monitors health over time by diffing current
market state against the entry snapshot, and simulates leg adjustments.
The AI layer (backend/ai/) narrates these computed results in plain English
using either a template-based MockProvider or Claude — it never generates
financial numbers, only explains ones the quant engine produced. The FastAPI
layer exposes all of this via REST and WebSocket. The React frontend
consumes it with ECharts for visualizations and a WebSocket hook for
real-time health updates.

---

## Why No Investment Recommendations

SEBI regulations prohibit investment recommendations without an RIA licence.
This platform is a construction and analysis tool — the user always decides
what to trade. The AI only explains the mechanics of what the quant engine
computed. Every number the AI states is traceable to a deterministic
Black-Scholes computation.

---

## Demo Flow (for judges — 5 minutes)

1. Open http://localhost:5173
2. Add 4 legs for an Iron Condor on Nifty:
   - Sell 18700 PE, Buy 18500 PE, Sell 19300 CE, Buy 19500 CE
3. Click **Analyze** → see Greeks, payoff chart, assumption checks
4. Click **Stress Test** tab → see 35-scenario heatmap
5. Change a strike → see copilot hint appear below the leg
6. Click **Save & Monitor** → health monitor connects via WebSocket
7. Click **Simulate Adjustment** → modify a leg, click Compare

---

*MoneyLogix Strategy Builder | Built for MoneyLogix Internship Hackathon 2026*
Agentic Bros