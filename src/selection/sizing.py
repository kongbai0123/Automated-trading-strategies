from abc import ABC, abstractmethod


class SizingPolicy(ABC):
    @abstractmethod
    def size(self, *, reference_price: float, atr_value: float) -> int:
        raise NotImplementedError


class FixedUnitsSizingPolicy(SizingPolicy):
    def __init__(self, units: int) -> None:
        self._units = units

    def size(self, *, reference_price: float, atr_value: float) -> int:
        return self._units


class FixedNotionalSizingPolicy(SizingPolicy):
    def __init__(self, notional: float) -> None:
        self._notional = notional

    def size(self, *, reference_price: float, atr_value: float) -> int:
        return max(int(self._notional / reference_price), 1)


class VolatilityScaledSizingPolicy(SizingPolicy):
    def __init__(self, *, risk_budget: float, atr_multiple: float) -> None:
        self._risk_budget = risk_budget
        self._atr_multiple = atr_multiple

    def size(self, *, reference_price: float, atr_value: float) -> int:
        per_unit_risk = max(atr_value * self._atr_multiple, 0.01)
        return max(int(self._risk_budget / per_unit_risk), 1)
