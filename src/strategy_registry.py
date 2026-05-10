from typing import Type, Dict
from .strategies import (
    Strategy,
    RSIMACDStrategy,
    MACrossoverStrategy,
    BollingerBreakoutStrategy,
)


class StrategyRegistry:
    """
    Registry for trading strategies. Provides a central place to register and retrieve
    strategies by name for the UI.
    """

    _registry: Dict[str, Type[Strategy]] = {
        "RSI_MACD": RSIMACDStrategy,
        "MA_CROSSOVER": MACrossoverStrategy,
        "BOLLINGER_BREAKOUT": BollingerBreakoutStrategy,
    }

    @classmethod
    def get_available_strategies(cls) -> list[str]:
        return list(cls._registry.keys())

    @classmethod
    def get_strategy(cls, name: str, **kwargs) -> Strategy:
        if name not in cls._registry:
            raise ValueError(f"Strategy {name} not found in registry.")
        return cls._registry[name](**kwargs)

    @classmethod
    def register(cls, name: str, strategy_cls: Type[Strategy]):
        cls._registry[name] = strategy_cls
