from __future__ import annotations

from datetime import datetime
from pathlib import Path
from sqlite3 import OperationalError

import pandas as pd
import pytest

from src.market_data import (
    ControlledMarketDataError,
    LocalCsvProvider,
    MarketDataService,
    YahooFinanceProvider,
    classify_freshness,
)


def _sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [102.0, 103.0],
            "Low": [99.0, 100.0],
            "Close": [101.0, 102.0],
            "Volume": [1000, 1200],
        },
        index=pd.to_datetime(["2026-05-08", "2026-05-09"]),
    )


def test_yfinance_sqlite_error_retries_without_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = YahooFinanceProvider()
    calls = {"count": 0}

    def fake_download(symbol: str, period: str, interval: str) -> pd.DataFrame:
        calls["count"] += 1
        if calls["count"] == 1:
            raise OperationalError("unable to open database file")
        return _sample_frame()

    monkeypatch.setattr(provider, "_download", fake_download)

    result = provider.fetch("2330.TW", period="2y", interval="1d")

    assert calls["count"] == 2
    assert result.source == "live_yfinance"
    assert result.live_attempted is True
    assert result.fallback_used is False
    assert result.provider_name == "YahooFinanceProvider"
    assert result.attempted_sources == ["live_yfinance"]
    assert result.fetch_latency_ms is not None
    assert any("cache-disabled-retry" in warning for warning in result.warnings)


def test_live_fetch_failure_falls_back_to_local_csv(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _sample_frame().reset_index(names="Date").to_csv(data_dir / "2330.TW.csv", index=False)

    service = MarketDataService(
        live_provider=YahooFinanceProvider(
            download_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                OperationalError("disk I/O error")
            )
        ),
        local_provider=LocalCsvProvider(data_dir=data_dir),
    )

    result = service.fetch("2330.TW", period="2y", interval="1d")

    assert result.source == "local_csv"
    assert result.fallback_used is True
    assert result.live_attempted is True
    assert result.provider_name == "LocalCsvProvider"
    assert result.attempted_sources == ["live_yfinance", "local_csv"]
    assert result.cache_hit is True
    assert any("Live data unavailable" in warning for warning in result.warnings)


def test_live_fetch_success_returns_live_source(tmp_path: Path) -> None:
    live_provider = YahooFinanceProvider(download_fn=lambda *_args, **_kwargs: _sample_frame())
    local_provider = LocalCsvProvider(data_dir=tmp_path / "data")
    service = MarketDataService(live_provider=live_provider, local_provider=local_provider)

    result = service.fetch("2330.TW", period="2y", interval="1d")

    assert result.source == "live_yfinance"
    assert result.fallback_used is False


def test_local_csv_provider_supports_legacy_symbol_filename(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _sample_frame().reset_index(names="Date").to_csv(data_dir / "2330.TW.csv", index=False)

    provider = LocalCsvProvider(data_dir=data_dir)
    result = provider.fetch("2330.TW", period="2y", interval="1d")

    assert result.source == "local_csv"
    assert result.dataframe.empty is False
    assert result.last_bar_time == datetime(2026, 5, 9)
    assert result.data_freshness == "DELAYED"
    assert result.is_stale is False


def test_classify_freshness_uses_interval_specific_thresholds() -> None:
    now = datetime(2026, 5, 10, 12, 0, 0)

    assert classify_freshness(datetime(2026, 5, 10, 11, 58, 0), "1m", now=now) == "DELAYED"
    assert classify_freshness(datetime(2026, 5, 10, 11, 0, 0), "1m", now=now) == "STALE"
    assert classify_freshness(datetime(2026, 5, 9, 0, 0, 0), "1d", now=now) == "DELAYED"


def test_market_data_service_raises_controlled_error_when_all_sources_fail(
    tmp_path: Path,
) -> None:
    service = MarketDataService(
        live_provider=YahooFinanceProvider(
            download_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                OperationalError("unable to open database file")
            )
        ),
        local_provider=LocalCsvProvider(data_dir=tmp_path / "data"),
    )

    with pytest.raises(ControlledMarketDataError, match="Unable to load market data for 2330.TW"):
        service.fetch("2330.TW", period="2y", interval="1d")
