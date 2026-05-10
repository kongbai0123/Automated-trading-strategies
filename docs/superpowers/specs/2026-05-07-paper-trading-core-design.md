# Paper Trading Core Design

## 1. Goal

Build a commercial-grade Phase 1 trading core for the existing Python trading workspace.

This phase delivers a deterministic paper trading engine with:

- Full order lifecycle management
- Portfolio accounting
- Risk evaluation as a first-class domain concern
- Append-only audit journal
- Replay support
- Broker adapter abstraction
- Semi-auto approval workflow

The system target is:

`Paper Trading Core + Broker Adapter Interface + Semi-Auto Ready`

The system target is not:

`strategy signal -> direct live order`

## 2. Non-goals

This phase does not include:

- Live broker execution
- Real exchange connectivity
- WebSocket reconnect handling
- Margin, leverage, short borrow, or derivatives settlement
- Multi-user SaaS tenancy
- OMS/EMS UI completion
- AI-driven execution decisions
- Tick-level matching engine fidelity

## 3. Architecture Overview

Phase 1 will be implemented in the existing Python domain layer under `src/trading/`.

The current repository already has reusable building blocks in `src/strategies.py`, `src/backtest.py`, `src/indicators.py`, and related tests. The new trading core will sit beside those modules instead of expanding [app.py](/D:/stock/app.py).

Primary architectural rules:

- Domain models come first and remain UI-independent.
- Trading engine orchestration is separate from strategy logic.
- Risk, execution, portfolio accounting, and journaling are isolated modules.
- The broker layer is interface-driven and starts with a paper adapter.
- Historical state is reconstructed from append-only events, not mutable snapshots alone.

Proposed module layout:

- `src/trading/models.py`
- `src/trading/events.py`
- `src/trading/journal.py`
- `src/trading/portfolio.py`
- `src/trading/risk.py`
- `src/trading/orders.py`
- `src/trading/brokers.py`
- `src/trading/execution.py`
- `src/trading/engine.py`

## 4. Event Flow

Canonical Phase 1 event flow:

```text
Strategy.generate_signals(df)
-> SignalEvent
-> OrderIntent
-> RiskDecision
-> PENDING_APPROVAL or OrderRequest
-> PaperBrokerAdapter.submit_order()
-> OrderAccepted / FillEvent
-> PortfolioEngine.apply_fill()
-> PortfolioSnapshot
-> Journal.append()
```

Execution policy for this phase:

- Signals are analytical outputs, not executable orders.
- Next-bar execution is the default policy.
- `market_time` is the bar timestamp used by the strategy.
- `created_at` is when the system emitted the domain object.
- `processed_at` is when the engine handled that object.
- Semi-auto mode stops after risk approval and waits for operator approval before execution.

## 5. Core Domain Models

### 5.1 Identity Requirements

All critical domain objects must have deterministic or traceable IDs.

Required IDs:

- `run_id`
- `strategy_id`
- `signal_id`
- `intent_id`
- `order_id`
- `fill_id`
- `portfolio_snapshot_id`
- `risk_decision_id`

Rules:

- IDs must be stable enough for replay, audit, and traceability.
- ID generation must not depend on hidden mutable global state.
- Related objects must retain parent references such as `signal_id` on `OrderIntent` and `intent_id` on `Order`.

### 5.2 Timestamp Requirements

Every event-like object must distinguish system time from market time.

Required fields:

- `created_at`
- `market_time`
- `processed_at`

Definitions:

- `created_at`: wall-clock time when the object was emitted
- `market_time`: timestamp of the source market bar or data point
- `processed_at`: engine processing time, especially useful for queueing or replay

### 5.3 SignalEvent

Represents a normalized strategy output.

Minimum fields:

- `signal_id`
- `run_id`
- `strategy_id`
- `symbol`
- `timeframe`
- `side`
- `signal_type`
- `strength`
- `confidence`
- `market_time`
- `created_at`
- `processed_at`
- `metadata`

`SignalEvent` is never treated as an order.

### 5.4 OrderIntent

Represents the engine's intention to express a trade idea after signal normalization.

Minimum fields:

- `intent_id`
- `signal_id`
- `run_id`
- `strategy_id`
- `symbol`
- `timeframe`
- `side`
- `quantity_policy`
- `requested_quantity`
- `order_type`
- `limit_price`
- `stop_price`
- `reason`
- `status`
- `expires_at`
- `market_time`
- `created_at`
- `processed_at`
- `metadata`

Required status values:

- `PENDING_RISK_CHECK`
- `RISK_APPROVED`
- `RISK_REJECTED`
- `PENDING_APPROVAL`
- `APPROVED_FOR_EXECUTION`
- `EXPIRED`

### 5.5 RiskDecision

`RiskDecision` must be a first-class domain object, not a boolean.

Minimum fields:

- `risk_decision_id`
- `intent_id`
- `approved`
- `reasons`
- `severity`
- `adjusted_quantity`
- `risk_score`
- `constraints_checked`
- `created_at`
- `processed_at`

This object defines whether the intent is rejected, resized, or allowed to proceed.

### 5.6 Order and Fill

Orders and fills are separate objects.

Order minimum fields:

- `order_id`
- `intent_id`
- `symbol`
- `side`
- `order_type`
- `quantity`
- `filled_quantity`
- `remaining_quantity`
- `status`
- `submitted_at`
- `market_time`
- `processed_at`

Fill minimum fields:

- `fill_id`
- `order_id`
- `symbol`
- `side`
- `fill_quantity`
- `fill_price`
- `commission`
- `slippage`
- `filled_at`
- `market_time`
- `processed_at`

`OrderIntent` is not an executed trade. `Order` is not a `Fill`.

## 6. Engine Responsibilities

### 6.1 Signal Engine

Responsibilities:

- Consume strategy outputs
- Normalize raw signals into `SignalEvent`
- Attach strategy, symbol, timeframe, and timestamp metadata

Non-responsibilities:

- Position sizing
- Order submission
- Portfolio mutation

### 6.2 Intent Engine

Responsibilities:

- Convert `SignalEvent` into `OrderIntent`
- Apply execution policy defaults
- Attach reason strings and quantity policy metadata

### 6.3 Risk Engine

Responsibilities:

- Evaluate each intent against configured constraints
- Produce `RiskDecision`
- Resize or reject intent when needed
- Prevent duplicate execution paths

### 6.4 Order Engine

Responsibilities:

- Convert approved intents into executable orders
- Track order state transitions
- Enforce valid lifecycle transitions

### 6.5 Execution Simulator

Responsibilities:

- Simulate paper fills for market and limit orders
- Apply slippage and commission models
- Support full and partial fills

### 6.6 Portfolio Engine

Responsibilities:

- Update cash, positions, average cost, realized PnL, unrealized PnL, and equity
- Apply fills deterministically
- Emit portfolio snapshots after state changes

### 6.7 Journal

Responsibilities:

- Persist append-only domain events
- Support replay and audit
- Never mutate historical events

## 7. Risk Rules

Phase 1 risk controls must be explicit and configurable.

Initial rule set:

- Max position size per symbol
- Max gross exposure
- Cash availability
- Duplicate signal / duplicate intent prevention
- Duplicate open-order prevention
- Strategy cooldown window
- Symbol allowlist or blocklist
- Daily loss cap
- Intent expiry

Risk evaluation output must include:

- Approval status
- Human-readable rejection or adjustment reasons
- Severity
- Adjusted quantity if resized
- Risk score
- Constraints checked

## 8. Order Lifecycle

Order lifecycle must be explicit and replayable.

Order states for Phase 1:

- `NEW`
- `ACCEPTED`
- `PARTIALLY_FILLED`
- `FILLED`
- `REJECTED`
- `CANCELLED`
- `EXPIRED`

Lifecycle rules:

- Orders are created only from intents that are execution-approved.
- Partial fills must preserve remaining quantity.
- Final fill transitions the order to `FILLED`.
- Invalid transitions must fail fast.

## 9. Portfolio Accounting

Portfolio accounting must prioritize correctness and replayability over cosmetic KPIs.

Phase 1 portfolio scope:

- Cash balance
- Position quantity per symbol
- Average cost per symbol
- Realized PnL
- Unrealized PnL
- Equity
- Exposure

Accounting rules:

- Fills are the only source of executed position change.
- Portfolio updates happen after each fill event.
- Snapshots can be stored for convenience, but replay source of truth is the event journal.
- Position accounting must be deterministic across replay runs.

## 10. Broker Adapter Interface

The broker layer must be interface-driven so the paper adapter and future live adapters share a contract.

Phase 1 interface:

- `submit_order(order_request) -> OrderAccepted | OrderRejected`
- `cancel_order(order_id) -> OrderCancelled | OrderCancelRejected`
- `get_order(order_id) -> Order`
- `list_open_orders() -> list[Order]`
- `get_positions() -> list[BrokerPosition]`

Phase 1 implementation:

- `PaperBrokerAdapter`

Rules:

- The engine depends on the adapter interface, not the concrete paper implementation.
- The adapter does not own portfolio accounting.
- The adapter can simulate fills, but fill application remains a portfolio concern.

## 11. Journal / Replay / Audit

Journal design is append-only.

Allowed event examples:

- `SIGNAL_EMITTED`
- `INTENT_CREATED`
- `RISK_APPROVED`
- `RISK_REJECTED`
- `INTENT_PENDING_APPROVAL`
- `ORDER_SUBMITTED`
- `ORDER_ACCEPTED`
- `ORDER_PARTIALLY_FILLED`
- `ORDER_FILLED`
- `ORDER_CANCELLED`
- `PORTFOLIO_SNAPSHOT`

Rules:

- Historical events are never updated in place.
- State changes are represented by new events.
- Replay rebuilds current state from ordered journal events.
- Audit queries must be able to follow `signal_id -> intent_id -> order_id -> fill_id`.

## 12. Semi-Auto Mode

Semi-auto mode is a first-class operating mode.

Behavior:

- After a `RiskDecision` with approval, the intent transitions to `PENDING_APPROVAL`.
- No broker submission occurs until operator approval is recorded.
- Approval emits a new event and transitions the intent to `APPROVED_FOR_EXECUTION`.
- Approval can expire based on intent expiry policy.

This prevents risk-approved intents from implicitly becoming executable trades.

## 13. Determinism Requirements

Determinism is mandatory for replay, testing, and commercial auditability.

Requirements:

- Next-bar execution policy must be explicit and testable.
- ID generation must be stable or traceable.
- Slippage and commission models must be configurable and deterministic in tests.
- Replay over the same event stream must rebuild the same portfolio state.
- No engine module may rely on hidden global state or UI session state.

## 14. Test Plan

Phase 1 will be implemented with TDD in pytest.

Initial tests:

- `test_signal_to_intent`
- `test_risk_rejects_duplicate_signal`
- `test_risk_rejects_excess_position_size`
- `test_semi_auto_stops_at_pending_approval`
- `test_order_lifecycle_market_fill`
- `test_partial_fill_then_final_fill`
- `test_portfolio_updates_cash_position_avg_price`
- `test_journal_append_only`
- `test_replay_reconstructs_portfolio`
- `test_next_bar_execution_policy`

Implementation order:

1. `models.py`
2. `events.py`
3. `journal.py`
4. `portfolio.py`
5. `risk.py`
6. `orders.py`
7. `brokers.py`
8. `execution.py`
9. `engine.py`
10. tests

## 15. Self Review

Review results:

- Scope is limited to a single Phase 1 trading core and excludes live execution.
- The model boundaries are explicit: `SignalEvent != OrderIntent != Order != Fill`.
- Semi-auto behavior is specified and blocks implicit execution.
- Deterministic IDs, timestamps, and append-only journal constraints are explicit.
- Replay, audit, and portfolio accounting are treated as core requirements, not add-ons.

Open implementation constraint:

- The current Python codebase will need a dedicated `src/trading/` package to avoid growing [app.py](/D:/stock/app.py) and unrelated existing modules.
