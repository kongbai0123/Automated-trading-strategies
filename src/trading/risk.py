from dataclasses import dataclass
from datetime import datetime, timedelta

from .models import (
    DecisionStatus,
    OrderIntent,
    PortfolioState,
    PositionState,
    RiskDecision,
    generate_trace_id,
)


@dataclass(frozen=True)
class RiskConfig:
    max_position_size: int
    max_symbol_exposure: float
    max_total_exposure: float
    max_daily_loss: float
    semi_auto: bool
    cooldown_minutes: int = 0
    symbol_allowlist: set[str] | None = None


class RiskEngine:
    def __init__(self, config: RiskConfig) -> None:
        self._config = config

    def evaluate(
        self,
        intent: OrderIntent,
        portfolio: PortfolioState | None,
        open_orders: list[object],
        reference_price: float = 1.0,
        seen_signal_ids: set[str] | None = None,
        last_entry_times: dict[str, datetime] | None = None,
        portfolio_state: PortfolioState | None = None,
    ) -> RiskDecision:
        portfolio = portfolio_state or portfolio or PortfolioState.initial(cash=0.0)
        reject_reasons: list[str] = []
        warning_reasons: list[str] = []
        constraints_checked: list[str] = []

        constraints_checked.append("intent_expiry")
        if intent.expires_at < intent.market_time:
            reject_reasons.append("intent_expired")

        if self._config.symbol_allowlist is not None:
            constraints_checked.append("symbol_allowlist")
            if intent.symbol not in self._config.symbol_allowlist:
                reject_reasons.append("symbol_allowlist")

        constraints_checked.append("duplicate_signal")
        if seen_signal_ids is not None and intent.signal_id in seen_signal_ids:
            reject_reasons.append("duplicate_signal")

        constraints_checked.append("cooldown")
        if self._config.cooldown_minutes > 0 and last_entry_times:
            last_entry = last_entry_times.get(intent.symbol)
            if last_entry is not None:
                if intent.market_time < last_entry + timedelta(
                    minutes=self._config.cooldown_minutes
                ):
                    reject_reasons.append("cooldown")

        constraints_checked.append("max_position_size")
        if intent.requested_quantity > self._config.max_position_size:
            reject_reasons.append("max_position_size")

        if reference_price > 0:
            estimated_notional = intent.requested_quantity * reference_price
            current_position = portfolio.positions.get(
                intent.symbol,
                PositionState(symbol=intent.symbol, quantity=0, average_price=0.0),
            )

            constraints_checked.append("max_symbol_exposure")
            next_symbol_exposure = (
                current_position.quantity * reference_price
            ) + estimated_notional
            if next_symbol_exposure > self._config.max_symbol_exposure:
                reject_reasons.append("max_symbol_exposure")

            constraints_checked.append("max_total_exposure")
            if portfolio.gross_exposure + estimated_notional > self._config.max_total_exposure:
                reject_reasons.append("max_total_exposure")

            constraints_checked.append("cash_constraint")
            if portfolio.cash < estimated_notional:
                reject_reasons.append("cash_constraint")

        constraints_checked.append("duplicate_open_order")
        if any(
            getattr(order, "symbol", None) == intent.symbol
            and getattr(order, "side", None) == intent.side
            for order in open_orders
        ):
            reject_reasons.append("duplicate_open_order")

        constraints_checked.append("max_daily_loss")
        if portfolio.realized_pnl <= -self._config.max_daily_loss:
            reject_reasons.append("max_daily_loss")

        approved = len(reject_reasons) == 0
        decision_status = DecisionStatus.APPROVED
        if not approved:
            decision_status = DecisionStatus.REJECTED
        elif warning_reasons:
            decision_status = DecisionStatus.APPROVED_WITH_WARNINGS

        return RiskDecision(
            risk_decision_id=generate_trace_id("risk", intent.intent_id),
            intent_id=intent.intent_id,
            approved=approved,
            decision_status=decision_status,
            reject_reasons=reject_reasons,
            warning_reasons=warning_reasons,
            adjusted_quantity=min(intent.requested_quantity, self._config.max_position_size),
            risk_score=(
                len(reject_reasons) / max(len(constraints_checked), 1)
                if reject_reasons
                else len(warning_reasons) / max(len(constraints_checked), 1)
            ),
            constraints_checked=constraints_checked,
            created_at=intent.created_at,
            processed_at=intent.processed_at,
        )
