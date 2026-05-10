from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any

import pandas as pd


def ensure_json_safe(value: Any) -> Any:
    if is_dataclass(value):
        return ensure_json_safe(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): ensure_json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [ensure_json_safe(item) for item in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except ValueError:
            pass
    return value


def dataframe_tail_records(dataframe: pd.DataFrame, *, limit: int = 5) -> list[dict]:
    records = dataframe.tail(limit).reset_index().to_dict(orient="records")
    return ensure_json_safe(records)
