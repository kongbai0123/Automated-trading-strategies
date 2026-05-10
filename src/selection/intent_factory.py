from datetime import timedelta

from src.selection.scoring import CandidateScore
from src.selection.sizing import SizingPolicy
from src.trading.models import OrderIntent, SignalEvent, generate_trace_id


class IntentFactory:
    def create_intent(
        self,
        *,
        signal: SignalEvent,
        requested_quantity: int,
        quantity_policy: str,
        order_type: str,
        reason: str,
        expires_at,
    ) -> OrderIntent:
        return OrderIntent.from_signal(
            signal=signal,
            intent_id=generate_trace_id("intent", signal.signal_id, order_type.lower()),
            quantity_policy=quantity_policy,
            requested_quantity=requested_quantity,
            order_type=order_type,
            reason=reason,
            expires_at=expires_at,
        )

    def create_from_candidate(
        self,
        *,
        candidate: CandidateScore,
        run_id: str,
        timeframe: str,
        sizing_policy: SizingPolicy,
        order_type: str,
    ) -> OrderIntent:
        signal = SignalEvent(
            signal_id=generate_trace_id("signal", run_id, candidate.symbol, candidate.market_time.isoformat()),
            run_id=run_id,
            strategy_id=candidate.strategy_id,
            symbol=candidate.symbol,
            timeframe=timeframe,
            side=candidate.side,
            signal_type="ENTRY",
            strength=candidate.setup_score,
            confidence=candidate.confidence,
            market_time=candidate.market_time,
            created_at=candidate.market_time,
            processed_at=candidate.market_time,
            metadata={
                "trend_score": candidate.trend_score,
                "volume_ratio": candidate.volume_ratio,
                "regime": candidate.regime.value,
            },
        )
        quantity = sizing_policy.size(reference_price=100.0, atr_value=1.0)
        return self.create_intent(
            signal=signal,
            requested_quantity=quantity,
            quantity_policy=sizing_policy.__class__.__name__,
            order_type=order_type,
            reason=f"ranked candidate score={candidate.setup_score}",
            expires_at=candidate.market_time + timedelta(days=1),
        )
