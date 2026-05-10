# Paper Trading Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the Phase 1 paper trading core so journal, replay, duplicate protection, risk checks, order lifecycle, and portfolio accounting match the approved design baseline.

**Architecture:** Keep the current `src/trading/` module boundaries, but strengthen them with explicit domain events, deterministic replay from journaled initialization state, risk rules that only report checks actually executed, and order/portfolio transitions that fail fast on invalid state. The engine remains orchestration-only and emits a complete audit chain from signal through fill and portfolio snapshot.

**Tech Stack:** Python 3.10+, `dataclasses`, `enum`, `typing`, `pytest`

---

## File Map

- Modify: `src/trading/models.py`
- Modify: `src/trading/events.py`
- Modify: `src/trading/journal.py`
- Modify: `src/trading/portfolio.py`
- Modify: `src/trading/risk.py`
- Modify: `src/trading/orders.py`
- Modify: `src/trading/brokers.py`
- Modify: `src/trading/engine.py`
- Modify: `src/trading/__init__.py`
- Modify: `tests/test_trading_engine.py`
- Modify: `tests/test_trading_risk.py`
- Modify: `tests/test_trading_orders.py`
- Modify: `tests/test_trading_portfolio.py`

## Task 1: Add failing tests for audit chain and replay initialization
- [ ] Add engine tests that require `PORTFOLIO_INITIALIZED`, full audit-chain events, and duplicate signal rejection in semi-auto mode.
- [ ] Run the focused engine tests and verify they fail for the expected reasons.

## Task 2: Add failing tests for risk rules
- [ ] Add tests for gross exposure, cash availability, duplicate open order, and expired intent rejection.
- [ ] Run the focused risk tests and verify they fail.

## Task 3: Add failing tests for order and portfolio state handling
- [ ] Add tests for invalid order transitions, overfill rejection, and sell-fill realized PnL handling.
- [ ] Run the focused order and portfolio tests and verify they fail.

## Task 4: Implement minimal model and event changes
- [ ] Add the missing portfolio, broker, and event metadata required by the tests.
- [ ] Keep IDs deterministic and preserve timestamp separation.

## Task 5: Implement minimal behavior changes
- [ ] Make journal/query helpers support duplicate detection and audit traversal.
- [ ] Make replay require initialization events instead of hard-coded cash.
- [ ] Make risk checks explicit and truthful.
- [ ] Make order transitions and portfolio accounting fail fast on invalid state.
- [ ] Emit the complete event chain from engine flow.

## Task 6: Verify
- [ ] Run the focused trading suite.
- [ ] Inspect output and only then summarize the repaired behavior and any residual risk.
