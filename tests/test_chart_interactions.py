from __future__ import annotations

import pandas as pd

from src.charting import DEFAULT_VISIBLE_BARS, create_price_chart
from src.ui.components.chart_workspace import CHART_INTERACTION_CONFIG


def _price_frame(rows: int = 240) -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=rows, freq="D")
    return pd.DataFrame(
        {
            "open": range(rows),
            "high": range(1, rows + 1),
            "low": range(rows),
            "close": range(1, rows + 1),
            "volume": [1000] * rows,
        },
        index=index,
    )


def test_price_chart_focuses_on_recent_visible_bars_by_default() -> None:
    df = _price_frame(DEFAULT_VISIBLE_BARS + 40)

    figure = create_price_chart(df)

    assert figure.layout.xaxis.range[0] == df.index[-DEFAULT_VISIBLE_BARS]
    assert figure.layout.xaxis.range[1] == df.index[-1]


def test_price_chart_exposes_trading_interaction_controls() -> None:
    figure = create_price_chart(_price_frame())

    assert figure.layout.dragmode == "pan"
    assert figure.layout.hovermode == "x unified"
    assert figure.layout.xaxis.rangeslider.visible is True
    assert figure.layout.xaxis.showspikes is True
    assert figure.layout.yaxis.showspikes is True
    assert figure.layout.xaxis.rangeselector.buttons[0].step == "day"


def test_chart_workspace_enables_scroll_zoom() -> None:
    assert CHART_INTERACTION_CONFIG["scrollZoom"] is True
    assert CHART_INTERACTION_CONFIG["doubleClick"] == "reset+autosize"
