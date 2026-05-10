from dataclasses import dataclass
from datetime import datetime

from src.selection.regime import MarketRegime
from src.trading.models import OrderSide


@dataclass(frozen=True)
class CandidateSignal:
    symbol: str
    strategy_id: str
    side: OrderSide
    confidence: float
    trend_score: float
    volume_ratio: float
    regime: MarketRegime
    market_time: datetime


@dataclass(frozen=True)
class CandidateScore:
    symbol: str
    strategy_id: str
    side: OrderSide
    confidence: float
    trend_score: float
    volume_ratio: float
    regime: MarketRegime
    market_time: datetime
    setup_score: float


class CandidateScorer:
    def score(self, candidate: CandidateSignal) -> CandidateScore:
        regime_bonus = {
            MarketRegime.TRENDING: 0.15,
            MarketRegime.BALANCED: 0.05,
            MarketRegime.RISK_OFF: -0.25,
        }[candidate.regime]
        raw_score = (
            (candidate.confidence * 0.45)
            + (candidate.trend_score * 0.35)
            + (min(candidate.volume_ratio, 2.0) / 2.0 * 0.20)
            + regime_bonus
        )
        return CandidateScore(
            symbol=candidate.symbol,
            strategy_id=candidate.strategy_id,
            side=candidate.side,
            confidence=candidate.confidence,
            trend_score=candidate.trend_score,
            volume_ratio=candidate.volume_ratio,
            regime=candidate.regime,
            market_time=candidate.market_time,
            setup_score=round(raw_score, 4),
        )
