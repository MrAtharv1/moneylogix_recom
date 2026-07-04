Here is the **updated `README.md`** that reflects **all the new features and fixes** you've implemented (Risk‑Appetite Recommender, Strike Ladder, Strategy Templates, Sentiment Detection, and all the UI/UX enhancements).

---

```markdown
# MoneyLogix Strategy Builder

> **AI‑native options strategy lifecycle platform for Indian index options.**
> Users construct multi‑leg strategies. The system analyzes, monitors, stress‑tests, and explains them in real time — **without ever making investment recommendations**.

---

## 📋 Prerequisites

- **Python 3.11+** installed
- **Node.js 18+** installed
- **Git** installed
- **A modern browser** (Chrome / Edge / Firefox)

---

## 🚀 How to Run (3 Terminals)

### Terminal 1 — Backend API

```bash
cd moneylogix-strategy-builder/backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

pip install -r ../requirements.txt
uvicorn main:app --reload --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     MoneyLogix Strategy Builder started | AI provider: mock | Environment: development
```

Keep this terminal open. Backend runs on **http://localhost:8000**

---

### Terminal 2 — Frontend (React + Vite)

```bash
cd moneylogix-strategy-builder/frontend
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
cd moneylogix-strategy-builder/backend
source venv/bin/activate   # or venv\Scripts\activate on Windows
pytest tests/ -v
```

**Expected output:**
```
============================= test session starts ==============================
collected 72+ items
tests/test_blackscholes.py ............                                    [25%]
tests/test_payoff.py .............                                          [37%]
tests/test_portfolio_greeks.py ........                                     [50%]
tests/test_assumption_checker.py ........                                   [62%]
tests/test_stress_test.py ......                                            [70%]
tests/test_fallback.py ..                                                   [72%]
tests/test_strategy_builder.py ....                                         [78%]
tests/test_adjustment_simulator.py .....                                    [85%]
tests/test_health_monitor.py ......                                         [92%]
tests/test_snapshot.py ....                                                 [100%]
============================= 72+ passed in 3.12s =============================
```

All tests must pass before the demo. Fix any failures by checking Terminal 1 for errors.

---

## ✅ Verify Everything is Connected

With both **Terminal 1** and **Terminal 2** running:

1. Open **http://localhost:5173** — dark UI should load
2. Open **http://localhost:8000/health** — should return `{"status":"ok"}`
3. Click any **Recommender profile** (Conservative / Moderate / Aggressive) — strategy should load automatically
4. Or, add legs manually and click **Analyze** — metrics, payoff chart, and Greeks should appear

If metrics don't appear, check **Terminal 1** for Python errors.

---

## 🧱 Project Structure (After All Fixes)

```
moneylogix-strategy-builder/
├── backend/
│   ├── main.py                  ← FastAPI app, all REST routes + WebSocket
│   ├── config.py                ← All settings from .env (AI_PROVIDER, CORS, etc.)
│   ├── models.py                ← Pydantic models (Leg now has entry_price)
│   ├── database.py              ← SQLite CRUD with UPSERT support
│   ├── data/
│   │   ├── mock_data.py         ← Hardcoded option chain (Tier 4) — single source of truth
│   │   ├── cache.py             ← In‑memory TTL cache with max‑size eviction
│   │   ├── nse_fetcher.py       ← Live NSE API (computes DTE, fetches IV rank)
│   │   ├── historical.py        ← India VIX via yfinance (for IV rank)
│   │   └── fallback.py          ← 4‑tier cascade orchestrator (case‑insensitive)
│   ├── quant/                   ← All deterministic financial math
│   │   ├── blackscholes.py      ← BS pricing + Greeks (handles expiry day)
│   │   ├── portfolio_greeks.py  ← Aggregates per‑leg Greeks (uses real lot size 65)
│   │   ├── payoff.py            ← Payoff curve at expiry + unlimited risk detection
│   │   ├── iv_rank.py           ← IV rank (0‑100) and regime classification
│   │   ├── expected_move.py     ← Market‑implied expected move
│   │   ├── probability.py       ← Probability of profit (N(d2) / multi‑leg)
│   │   ├── margin.py            ← Simplified SPAN margin (handles unlimited sentinels)
│   │   ├── liquidity.py         ← Bid‑ask spread + OI + volume score
│   │   └── stress_test.py       ← 5×7 scenario matrix (price × IV shocks)
│   ├── engine/                  ← Orchestrators that glue quant modules together
│   │   ├── strategy_builder.py  ← Main orchestrator (DRY, fixed dict keys)
│   │   ├── assumption_checker.py← 4‑assumption check per strategy type
│   │   ├── health_monitor.py    ← Diffs current vs entry state (threshold‑based)
│   │   ├── adjustment_simulator.py ← Before/after leg change comparison (fixed theta key)
│   │   ├── snapshot.py          ← Thread‑safe in‑RAM persistence + dual‑write SQLite
│   │   └── ai_prompt_router.py  ← Natural‑language → strategy generator (respects AI_PROVIDER)
│   ├── ai/                      ← AI narration layer (pluggable)
│   │   ├── base_provider.py     ← Abstract interface
│   │   ├── mock_provider.py     ← Template‑based, no API key (fixed delta key)
│   │   ├── claude_provider.py   ← Claude API (f‑string safe, falls back to mock)
│   │   ├── hf_provider.py       ← HuggingFace API provider
│   │   ├── explainer.py         ← Lifecycle change explanation (public API)
│   │   └── copilot.py           ← Inline leg‑edit hints (public API)
│   ├── utils/
│   │   ├── logger.py            ← Structured JSON logging
│   │   └── validators.py        ← Input validation (dynamically uses ALL symbols from mock_data)
│   └── tests/                   ← 🧪 Complete test suite (72+ tests)
│       ├── test_blackscholes.py    ← 18 tests (all BS edge cases)
│       ├── test_payoff.py          ← 9 tests (payoff curves, breakevens, unlimited risk)
│       ├── test_portfolio_greeks.py← 10 tests (aggregation, P&L, scaling)
│       ├── test_assumption_checker.py ← 7 tests (strategy assumptions + number‑in‑reason)
│       ├── test_stress_test.py     ← 7 tests (matrix shape, center cell, extremes)
│       ├── test_fallback.py        ← 2 tests (valid structure, case‑insensitivity)
│       ├── test_strategy_builder.py← 4 tests (orchestrator keys, entry_price, risk score)
│       ├── test_adjustment_simulator.py ← 5 tests (comparison logic, net_theta fix, unlimited formatting)
│       ├── test_health_monitor.py  ← 6 tests (diff thresholds, DTE warning, multi‑change)
│       └── test_snapshot.py        ← 4 tests (in‑RAM persistence, dual‑write resilience)
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── tailwind.config.js        ← Added `tailwindcss-animate` plugin
│   ├── postcss.config.js
│   ├── vite.config.ts
│   └── src/
│       ├── main.tsx
│       ├── App.tsx               ← Router with 404 catch‑all
│       ├── index.css
│       ├── types/
│       │   └── strategy.ts       ← All TypeScript interfaces (mirrors models.py)
│       ├── api/
│       │   └── client.ts         ← Axios client (baseURL from env var)
│       ├── hooks/
│       │   ├── useStrategy.ts    ← Strategy state (useReducer + debounced auto‑analyze)
│       │   ├── useWebSocket.ts   ← Health monitor WebSocket (WS_URL from env var)
│       │   └── useOptionChain.ts ← Option chain fetcher (AbortController)
│       ├── utils/
│       │   ├── formatters.ts     ← formatINR (2 decimal places), formatDelta, etc.
│       │   ├── strategyLink.ts   ← URL share encode/decode (UUID for leg IDs)
│       │   ├── templateBuilder.ts← Strategy template leg builder (Iron Condor, Straddle, etc.)
│       │   └── recommenderEngine.ts ← Weighted scoring engine for 3‑profile recommender
│       ├── components/           ← All UI components (see below for breakdown)
│       └── pages/
│           ├── StrategyWorkspace.tsx  ← Main page (activeTab persisted in localStorage)
│           └── AdjustmentView.tsx     ← Before/after comparison (uses net_theta)
├── requirements.txt              ← Python dependencies
├── .env.example                  ← Template for environment variables
└── README.md                     ← This file
```

---

## 🆕 New Features

### 1. Risk‑Appetite Recommender (`RecommenderPanel.tsx`)
- **3‑click profiles:** Conservative, Moderate, Aggressive
- **Intelligent mapping:** Uses a weighted scoring engine with 4 signals:
  - IV Rank (volatility regime)
  - Days to Expiry (time horizon)
  - Expected Move (price uncertainty)
  - Risk Tier penalty (matches strategy to user's risk appetite)
- **"Next Best Action"** – shows top 2 alternative strategies with scores
- **Dynamic rationale** – explains why a strategy fits current market conditions

### 2. Live Strike Ladder (`StrikeLadder.tsx`)
- Collapsible table showing:
  - Strike Price (with ATM highlighting)
  - Call LTP, Call OI
  - Put LTP, Put OI
- **Click‑to‑populate** – clicking a strike adds a leg instantly
- Works with live NSE data, cache, snapshot, or demo mode

### 3. Strategy Templates (`templateBuilder.ts`)
- Dropdown in `LegBuilder` with one‑click templates:
  - Iron Condor, Long Straddle, Long Strangle
  - Bull Call Spread, Bull Put Spread
  - Bear Call Spread, Bear Put Spread
  - Covered Call
- **Snaps to real strikes** – uses actual strikes from the option chain (no arbitrary offsets)
- **Auto‑analyzes** – legs populate and analysis runs automatically

### 4. Sentiment Detection (`AIPromptInput.tsx`)
- Detects emotional cues in user input:
  - Fear → suggests defensive strategies
  - Greed → suggests defined‑risk strategies
  - Range‑bound view → suggests Iron Condor
  - Volatile view → suggests Long Straddle/Strangle
- Context‑aware phrase matching (not just raw word matching)
- Displays as a subtle badge below the input

---

## 📂 Brief: What Each Core File Does

| File / Folder | Purpose |
|---------------|---------|
| `main.py` | FastAPI entry point. All REST endpoints + WebSocket. Uses `lifespan` (modern). CORS from settings. Global exception handler **never leaks stack traces**. |
| `models.py` | Pydantic models. **`Leg` now has optional `entry_price`** – critical for correct P&L. |
| `strategy_builder.py` | Main orchestrator. Calls all quant modules. Returns metrics with **correct dict keys** (`net_delta`, `net_theta`, `leg_contributions`). Handles errors gracefully (logs + falls back). |
| `adjustment_simulator.py` | Before/after comparison. Uses `net_theta` (not `theta`). Handles unlimited profit/loss sentinels. |
| `payoff.py` | Payoff curve at expiry. **Fixed IndexError** when `num_points=1`. Detects unlimited risk. |
| `portfolio_greeks.py` | Aggregates Greeks. Uses **real lot size 65** (Nifty) instead of 50. |
| `blackscholes.py` | On expiry day (`T_days <= 0`), returns **intrinsic value** instead of zero. |
| `nse_fetcher.py` | Live NSE API. Computes `days_to_expiry` from expiry date. Fetches IV rank from historical VIX. If NSE lacks Greeks, computes them via BS. |
| `fallback.py` | 4‑tier cascade: Live → Cache → Snapshot → Mock. **Case‑insensitive cache key**. |
| `cache.py` | TTL cache with **max‑size eviction** (prevents unbounded memory growth). |
| `database.py` | SQLite persistence with **UPSERT** (re‑saving a strategy updates instead of crashing). |
| `snapshot.py` | In‑RAM `_DB` and `_HISTORY` are now **thread‑safe** (locks). Dual‑writes to SQLite but never fails if DB is down. |
| `validators.py` | Dynamically builds `VALID_SYMBOLS` from `mock_data.asset_config` – **supports all 200+ stocks**. |
| `mock_provider.py` | Template‑based AI. **Fixed delta key** (now uses `"delta"` not `"portfolio_delta"`). |
| `claude_provider.py` | Claude API. **Safe f‑string formatting** (handles missing `spot` gracefully). Falls back to mock on any failure. |
| `hf_provider.py` | HuggingFace API provider. Falls back to mock on any failure. |
| `ai_prompt_router.py` | Natural‑language → strategy generator. **Respects `AI_PROVIDER` config** (if not `huggingface`, skips API). Recognises all strategy types (Condor, Straddle, Strangle, Bear/Bull spreads, Covered Call). |
| `templateBuilder.ts` (frontend) | Pure utility that builds leg arrays for strategy templates (Iron Condor, Straddle, etc.) **snapping to real strikes**. |
| `recommenderEngine.ts` (frontend) | Weighted scoring engine for the 3‑profile recommender. Uses IV Rank, DTE, Expected Move, and Risk Tier. |
| `RecommenderPanel.tsx` (frontend) | 3‑click profile cards (Conservative / Moderate / Aggressive) with dynamic strategy recommendations and rationale. |
| `StrikeLadder.tsx` (frontend) | Collapsible live options chain table with click‑to‑populate‑leg functionality. |
| `client.ts` (frontend) | Axios client. **Base URL from `VITE_API_BASE_URL` env var** – no more hardcoded localhost. |
| `useWebSocket.ts` (frontend) | WebSocket connection. **WS URL from `VITE_WS_BASE_URL` env var**. Proper error handling. |
| `useStrategy.ts` (frontend) | Strategy state. **Added `triggerAutoAnalyze`** – debounced auto‑analysis on leg edits (500ms). |
| `LegRow.tsx` (frontend) | **Fixed `prevLegRef` ordering** – captures leg before edit, sends correct `before`/`after` to copilot. |
| `formatters.ts` (frontend) | **Fixed `formatINR`** – now shows 2 decimal places (`maximumFractionDigits: 2`). |
| `strategyLink.ts` (frontend) | **Leg IDs now use `uuidv4()`** – no more duplicate IDs in shared links. |
| `StrategyWorkspace.tsx` (frontend) | **Active tab persisted in `localStorage`**. Auto‑analysis on AI‑generated legs. Template loading with visual feedback. |
| `AdjustmentView.tsx` (frontend) | Uses `validStrategyType` check. Theta comparison uses `net_theta`. |

---

## 🔄 Switching AI Provider

By default the app uses **MockProvider** — no API key needed, works offline.

To switch to **HuggingFace** (free, open‑source model):

1. Create a `.env` file in the `backend/` folder:
```
AI_PROVIDER=huggingface
HUGGINGFACE_API_KEY=your_hf_token_here
```

2. Restart Terminal 1 (Ctrl+C then run `uvicorn` again)

To switch to **Claude**:
```
AI_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-...
```

To switch back to mock: set `AI_PROVIDER=mock` or delete the `.env` file.

---

## 🛡️ If NSE Data Fails (4‑Tier Fallback)

The app **never crashes** due to missing data. It falls back automatically:

```
Live NSE → Cache (60s) → SQLite Snapshot → Demo Mock Data
```

The **DataModeBanner** at the top of the page shows which source is active:

| Color | Mode | Meaning |
|-------|------|---------|
| 🟢 Green | **Live Data** | NSE API is working – real market prices |
| 🔵 Blue | **Cached Data** | Using cache (< 60s old) – NSE temporarily unreachable |
| 🟡 Yellow | **Snapshot Data** | Using last saved strategy snapshot – NSE and cache both failed |
| 🟠 Orange | **Demo Mode** | Using hardcoded sample data – full functionality preserved |

Full functionality works in **all four modes**. The quant engine never sees a `None` or `null` chain.

---

## 📡 API Endpoints Reference

| Method | Endpoint | What it does |
|--------|----------|--------------|
| GET | `/health` | Verify API is running |
| GET | `/option-chain/{symbol}` | Fetch Nifty/BankNifty chain (4‑tier) |
| POST | `/strategy/analyze` | Compute all metrics for legs |
| POST | `/strategy/payoff` | Payoff curve only (faster, **now computes entry_price**) |
| POST | `/strategy/assumptions` | Check 4 strategy assumptions |
| POST | `/strategy/stress-test` | 35‑scenario heatmap (**now computes entry_price**) |
| POST | `/strategy/time-decay` | Payoff snapshots over time (Time Slider) |
| POST | `/strategy/save` | Save strategy for monitoring (UPSERT) |
| GET | `/strategy/{id}/history` | Health event log |
| POST | `/adjustment/simulate` | Before/after comparison |
| POST | `/copilot/hint` | Inline leg‑edit hint |
| POST | `/explain` | Lifecycle change explanation |
| WS | `/ws/health/{id}` | Real‑time health monitor (WebSocket) |

Full interactive docs at **http://localhost:8000/docs** (auto‑generated by FastAPI)

---

## 🎬 Demo Flow (for Judges — 5 minutes)

### Option A: Using the Recommender (Guided Experience)
1. Open **http://localhost:5173**
2. Click **"Conservative"** → the Recommender loads an Iron Condor
3. Click **"Moderate"** → loads a Bull Put Spread or Iron Condor (based on IV)
4. Click **"Aggressive"** → loads a Long Straddle or Long Strangle
5. Each selection auto‑populates legs and runs analysis
6. View the Payoff Chart, Greeks, Risk Score, and Assumption Dashboard

### Option B: Using Strategy Templates
1. Open **http://localhost:5173**
2. In the **LegBuilder**, click **"Load Template"** dropdown
3. Select **"Iron Condor"** → 4 legs auto‑fill
4. Click **Analyze** → metrics appear
5. Try **"Long Straddle"** → 2 legs auto‑fill
6. Click **Analyze** → see the different payoff profile

### Option C: Manual Construction
1. Open **http://localhost:5173**
2. Click **"+ Add Leg"** → add 4 legs manually
3. Click **Analyze** → see the Greeks, payoff chart, and assumptions
4. Click **Stress Test** tab → see the 5×7 colour‑coded heatmap
5. **Edit a leg** (e.g., change strike) → **Copilot hint** appears below the leg within 300ms
6. Click **Save & Monitor** → Health Monitor connects via WebSocket
7. Click **Simulate Adjustment** → modify a leg, click **Compare Strategies**

### Option D: AI Copilot (Natural Language)
1. In the **"Strategy Copilot"** input box, type: *"I think NIFTY will stay range‑bound, budget ₹20,000"*
2. Click **Build** → the AI generates an Iron Condor with 4 legs
3. Notice the **sentiment badge** – if you type a fearful phrase, it shows "📉 Fear detected..."
4. Click **Analyze** → all metrics appear instantly

---

## 🐛 Common Issues and Fixes

**Backend won't start:**
```bash
# Make sure venv is activated
venv\Scripts\activate   # Windows
source venv/bin/activate # macOS/Linux
# Make sure you're in the backend folder
cd backend
# Try reinstalling
pip install -r ../requirements.txt
```

**Frontend shows blank page:**
```bash
# Check browser console for errors (F12)
# Make sure backend is running on port 8000
# Check that CORS in config.py allows http://localhost:5173
```

**"Analysis failed" in UI:**
- Check Terminal 1 for Python errors
- Verify `http://localhost:8000/health` returns 200
- Check the DataMode banner — if it shows Demo Mode, data is working, the issue is in computation

**WebSocket not connecting:**
- Make sure strategy is saved first (click "Save & Monitor")
- Check browser console — WebSocket URL must be `ws://` not `http://`
- Check Terminal 1 for WebSocket errors

**Template dropdown does nothing:**
- Wait for the **Strike Ladder** to load (this means the option chain is ready)
- If the dropdown is disabled, the chain is still loading – wait a second
- If you see "❌ Option chain is empty", check backend logs or refresh

**Tests failing:**
```bash
# Run just the failing test file with verbose output
pytest tests/test_blackscholes.py -v -s
# The -s flag shows print statements and logging
```

**`formattedType` is not defined (TypeScript error):**
- Already fixed in `StrategyWorkspace.tsx` — `strategyTypeFormatted` is now declared in the correct scope.

---

## 🧠 Architecture in One Paragraph

The **quant engine** (`backend/quant/`) computes all numbers using Black‑Scholes:
Greeks, payoff curves, IV rank, expected move, margin estimates, and stress
scenarios. The **lifecycle engine** (`backend/engine/`) orchestrates these into
complete strategy analysis, monitors health over time by diffing current
market state against the entry snapshot, and simulates leg adjustments.
The **AI layer** (`backend/ai/`) narrates these computed results in plain English
using either a template‑based MockProvider or Claude — it **never generates**
financial numbers, only explains ones the quant engine produced. The **FastAPI**
layer exposes all of this via REST and WebSocket. The **React frontend**
consumes it with ECharts for visualisations and a WebSocket hook for
real‑time health updates.

The **Recommender** (`frontend/src/utils/recommenderEngine.ts`) adds a
**weighted scoring engine** that maps user risk profiles to strategy
recommendations using IV Rank, Days to Expiry, and Expected Move.

---

## ⚖️ Why No Investment Recommendations

SEBI regulations prohibit investment recommendations without an RIA licence.
This platform is a **construction and analysis tool** — the user always decides
what to trade. The AI only explains the **mechanics** of what the quant engine
computed. Every number the AI states is traceable to a deterministic
Black‑Scholes computation. All AI outputs contain a disclaimer:
*"This is a mechanical evaluation, not investment advice."*

---

## 🧪 Test Coverage Summary

| Module | Tests | Key Checks |
|--------|-------|------------|
| `blackscholes.py` | 18 | ATM delta, deep ITM/OTM, put‑call parity, gamma/vega positivity, invalid inputs |
| `payoff.py` | 9 | Long call, short put, bull spread, iron condor, breakevens, unlimited risk |
| `portfolio_greeks.py` | 10 | Aggregation, P&L, scaling, offsetting hedge |
| `assumption_checker.py` | 7 | Strategy‑specific rules, reason strings contain numbers |
| `stress_test.py` | 7 | Matrix shape, center cell, IV crush, big move |
| `fallback.py` | 2 | Valid structure, case‑insensitivity |
| `strategy_builder.py` | 4 | Correct keys, entry_price, fallback, risk score |
| `adjustment_simulator.py` | 5 | Comparison structure, net_theta, unlimited formatting |
| `health_monitor.py` | 6 | Thresholds, DTE warning, multi‑change |
| `snapshot.py` | 4 | Persistence, history, dual‑write resilience |
| **Total** | **72+** | All critical modules covered |

---

*MoneyLogix Strategy Builder | Built for MoneyLogix Internship Hackathon 2026*
**Agentic Bros** 🚀
```
