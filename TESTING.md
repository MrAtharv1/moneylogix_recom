# Manual QA Checklist: MoneyLogix Strategy Builder

Follow this checklist to verify end-to-end functionality before the final hackathon submission.

### FLOW 1: Basic Strategy Analysis
- [ ] Backend starts: run `uvicorn main:app --reload --port 8000`
  - *Expected:* "MoneyLogix Strategy Builder API started" appears in logs.
- [ ] Frontend starts: run `npm run dev`
  - *Expected:* Page loads at `http://localhost:5173` with the dark background visible.
- [ ] GET `http://localhost:8000/health` returns 200
  - *Expected:* JSON response `{"status":"ok","ai_provider":"mock",...}`
- [ ] DataModeBanner appears at top of page
  - *Expected:* Green "● Live Data" or orange "Demo Mode" depending on NSE availability.
- [ ] Add an Iron Condor (4 legs):
  - Sell 18700 PE, Sell 19300 CE, Buy 18500 PE, Buy 19500 CE.
- [ ] Click "Analyze"
  - *Expected:* Loading spinner appears on the button.
- [ ] Metrics appear within 3 seconds:
  - [ ] Portfolio delta ≈ 0 (roughly delta-neutral).
  - [ ] Max loss is finite (not "Unlimited Loss" — Iron Condor is defined risk).
  - [ ] Max profit is finite.
  - [ ] At least 2 breakeven prices shown.
  - [ ] 4 assumption checks appear in the Assumptions tab.
- [ ] Switch to Payoff tab:
  - [ ] Chart renders with green and red regions.
  - [ ] Profit region is in the center (between the short strikes).
  - [ ] Vertical dashed lines show breakeven prices.
- [ ] Switch to Greeks tab:
  - [ ] PortfolioGreeks shows 4 values.
  - [ ] Net delta is close to 0.
  - [ ] Net theta is positive (benefits from time decay).
  - [ ] LegGreeksTable shows 4 rows (one per leg).

### FLOW 2: Stress Test
- [ ] Switch to "Stress Test" tab
  - *Expected:* "Computing 35 market scenarios..." spinner appears.
- [ ] Heatmap loads within 5 seconds.
- [ ] Center cell (0% price, 0pp IV change) shows ≈ ₹0.
- [ ] Top-right cell (+5% price, +30pp IV) shows a negative value (red).
- [ ] Center cells show positive values (green).
- [ ] All 35 cells are readable (text contrast is clear against the background color).
- [ ] "Worst case" and "Best case" are shown below the heatmap.

### FLOW 3: Save and Health Monitor
- [ ] Click "Save & Monitor"
  - *Expected:* Button shows loading, then HealthMonitor panel appears below.
- [ ] HealthMonitor shows "● Monitoring live" with a green dot.
- [ ] Wait 60 seconds.
  - *Expected:* "✓ No significant changes since entry — last checked {time}" appears OR diff badges appear if the market moved significantly.
- [ ] If an explanation appears:
  - [ ] Verify it contains at least one number.
  - [ ] Verify there is NO directive language (no "you should" or "I recommend").

### FLOW 4: Copilot Hint
- [ ] Add a leg and change the strike by 200 points.
  - *Expected:* After ~300ms, a hint appears below the leg row.
- [ ] Hint contains at least one number (delta or theta value).
- [ ] Hint disappears when you clear the input.
- [ ] Hint has NO directive language.

### FLOW 5: Adjustment Simulator
- [ ] With a strategy analyzed, click "Simulate Adjustment".
  - *Expected:* Navigates to the AdjustmentView page.
- [ ] Left column shows original legs (read-only).
- [ ] Modify a strike in the right column.
- [ ] Click "Compare".
  - *Expected:* Comparison cards appear below.
- [ ] Both payoff charts appear side by side.
- [ ] Both payoff charts use the same x-axis range (same min/max price).
- [ ] Summary sentence is factual with no investment advice.

### FLOW 6: Demo Mode (Critical for Day of Presentation)
- [ ] Stop the backend (Ctrl+C in terminal).
- [ ] Wait 5 seconds, then reload the frontend.
  - *Expected:* Orange "Demo Mode — using sample data" banner appears.
- [ ] Click Analyze with any legs.
  - *Expected:* Works with mock data, results appear normally.
- [ ] Verify there are no red console errors in browser developer tools.
- [ ] Start backend again.
  - *Expected:* Banner switches back to "● Live Data" or "Cached Data" on the next refresh.

### FLOW 7: Mobile / Narrow Screen
- [ ] Open browser, resize width to ~375px (mobile size).
- [ ] Layout collapses to a single column.
- [ ] All text remains readable (no overflow, no truncation).
- [ ] Payoff chart is still visible and correctly sized.
- [ ] Stress test heatmap is horizontally scrollable.