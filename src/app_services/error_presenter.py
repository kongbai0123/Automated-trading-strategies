from __future__ import annotations

from typing import Any


def build_controlled_error_payload(
    *,
    symbol: str,
    attempted_source: str,
    fallback_attempted: bool,
    diagnostics: dict[str, str],
    message: str,
) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "attempted_source": attempted_source,
        "fallback_attempted": fallback_attempted,
        "diagnostics": diagnostics,
        "message": message,
    }

