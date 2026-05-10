from datetime import datetime, timedelta

from src.selection.intent_factory import IntentFactory
from src.selection.ranking import RankingEngine
from src.selection.regime import MarketRegime, RegimeFilter
from src.selection.scoring import CandidateSignal, CandidateScorer
from src.selection.sizing import FixedNotionalSizingPolicy, FixedUnitsSizingPolicy, VolatilityScaledSizingPolicy
from src.trading.events import EventType
from src.trading.models import DecisionStatus, OrderSide, SignalEvent
from src.trading.risk import RiskConfig, RiskEngine


def test_event_type_taxonomy_contains_required_phase_2_events():
    expected = {
        "PORTFOLIO_INITIALIZED",
        "SIGNAL_EMITTED",
        "INTENT_CREATED",
        "RISK_APPROVED",
        "RISK_REJECTED",
        "INTENT_PENDING_APPROVAL",
        "INTENT_APPROVED_FOR_EXECUTION",
        "ORDER_SUBMITTED",
        "ORDER_ACCEPTED",
        "ORDER_PARTIALLY_FILLED",
        "ORDER_FILLED",
        "ORDER_REJECTED",
        "ORDER_CANCELLED",
        "FILL_RECORDED",
        "PORTFOLIO_UPDATED",
        "PORTFOLIO_SNAPSHOT",
    }

    assert {event_type.name for event_type in EventType} == expected


def test_cooldown_blocks_repeated_entry_and_uses_reason_buckets():
    signal = SignalEvent(
        signal_id="signal:cooldown",
        run_id="run-1",
        strategy_id="ma-cross",
        symbol="2330.TW",
        timeframe="1d",
        side=OrderSide.BUY,
        signal_type="ENTRY",
        strength=0.8,
        confidence=0.7,
        market_time=datetime(2026, 5, 10, 10, 0, 0),
        created_at=datetime(2026, 5, 10, 10, 0, 1),
        processed_at=datetime(2026, 5, 10, 10, 0, 2),
        metadata={},
    )
    intent = IntentFactory().create_intent(
        signal=signal,
        requested_quantity=10,
        quantity_policy="fixed_units",
        order_type="MARKET",
        reason="cooldown test",
        expires_at=signal.market_time + timedelta(days=1),
    )
    engine = RiskEngine(
        RiskConfig(
            max_position_size=100,
            max_symbol_exposure=50_000.0,
            max_total_exposure=100_000.0,
            max_daily_loss=50_000.0,
            semi_auto=True,
            cooldown_minutes=30,
            symbol_allowlist={"2330.TW"},
        )
    )

    decision = engine.evaluate(
        intent=intent,
        portfolio=None,
        portfolio_state=None,
        open_orders=[],
        reference_price=100.0,
        seen_signal_ids=set(),
        last_entry_times={"2330.TW": signal.market_time - timedelta(minutes=5)},
    )

    assert decision.approved is False
    assert decision.decision_status is DecisionStatus.REJECTED
    assert "cooldown" in decision.reject_reasons
    assert "cooldown" in decision.constraints_checked
    assert decision.warning_reasons == []


def test_selection_flow_ranks_candidates_and_creates_intent():
    candidate_a = CandidateSignal(
        symbol="2330.TW",
        strategy_id="RSI_MACD",
        side=OrderSide.BUY,
        confidence=0.8,
        trend_score=0.9,
        volume_ratio=1.8,
        regime=MarketRegime.TRENDING,
        market_time=datetime(2026, 5, 10, 9, 0, 0),
    )
    candidate_b = CandidateSignal(
        symbol="2317.TW",
        strategy_id="MA_CROSSOVER",
        side=OrderSide.BUY,
        confidence=0.6,
        trend_score=0.5,
        volume_ratio=1.1,
        regime=MarketRegime.BALANCED,
        market_time=datetime(2026, 5, 10, 9, 0, 0),
    )

    scorer = CandidateScorer()
    ranked = RankingEngine().rank(
        [scorer.score(candidate_a), scorer.score(candidate_b)]
    )
    top = ranked[0]
    intent = IntentFactory().create_from_candidate(
        candidate=top,
        run_id="run-1",
        timeframe="1d",
        sizing_policy=FixedUnitsSizingPolicy(25),
        order_type="MARKET",
    )

    assert top.symbol == "2330.TW"
    assert intent.symbol == "2330.TW"
    assert intent.requested_quantity == 25


def test_sizing_policies_return_expected_quantities():
    fixed_units = FixedUnitsSizingPolicy(20)
    fixed_notional = FixedNotionalSizingPolicy(50_000.0)
    volatility_scaled = VolatilityScaledSizingPolicy(risk_budget=2_000.0, atr_multiple=2.0)

    assert fixed_units.size(reference_price=100.0, atr_value=2.0) == 20
    assert fixed_notional.size(reference_price=100.0, atr_value=2.0) == 500
    assert volatility_scaled.size(reference_price=100.0, atr_value=5.0) == 200


def test_regime_filter_identifies_risk_off_environment():
    regime = RegimeFilter().classify(trend_score=0.2, volatility_score=0.95)

    assert regime is MarketRegime.RISK_OFF
