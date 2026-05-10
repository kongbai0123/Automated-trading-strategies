from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from sqlite3 import OperationalError
from time import perf_counter

import pandas as pd
import yfinance as yf
import yfinance.cache as yf_cache

from .data_loader import load_csv, validate_ohlcv

DownloadFn = Callable[[str, str, str], pd.DataFrame]

SQLITE_ERROR_MARKERS = (
    "unable to open database file",
    "disk i/o error",
    "database is locked",
    "sqlite",
)


@dataclass(frozen=True)
class MarketDataResult:
    dataframe: pd.DataFrame
    source: str
    live_attempted: bool
    fallback_used: bool
    warnings: list[str]
    diagnostics: dict[str, object]
    data_freshness: str
    last_bar_time: datetime | None
    is_stale: bool
    provider_name: str = ""
    attempted_sources: list[str] | None = None
    fetch_latency_ms: int | None = None
    cache_hit: bool = False


class ControlledMarketDataError(RuntimeError):
    def __init__(
        self,
        *,
        symbol: str,
        attempted_source: str,
        fallback_attempted: bool,
        diagnostics: dict[str, object],
    ) -> None:
        self.symbol = symbol
        self.attempted_source = attempted_source
        self.fallback_attempted = fallback_attempted
        self.diagnostics = diagnostics
        super().__init__(f"Unable to load market data for {symbol}")


def _normalize_live_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        raise ValueError("Live provider returned empty data")
    frame = df.copy()
    if isinstance(frame.index, pd.DatetimeIndex) and frame.index.tz is not None:
        frame.index = frame.index.tz_localize(None)
    frame = frame.reset_index()
    frame = frame.rename(columns={"Date": "date", "Datetime": "date", "index": "date"})
    return validate_ohlcv(frame)


def _last_bar_time(df: pd.DataFrame) -> datetime | None:
    if df.empty:
        return None
    index_value = df.index[-1]
    if isinstance(index_value, pd.Timestamp):
        return index_value.to_pydatetime()
    return pd.Timestamp(index_value).to_pydatetime()


def classify_freshness(
    last_bar_time: datetime | None,
    interval: str,
    *,
    now: datetime | None = None,
) -> str:
    if last_bar_time is None:
        return "UNKNOWN"

    now = now or datetime.now()
    age_seconds = max(0.0, (now - last_bar_time).total_seconds())
    max_age_seconds_by_interval = {
        "1m": 5 * 60,
        "5m": 15 * 60,
        "15m": 45 * 60,
        "30m": 90 * 60,
        "60m": 3 * 60 * 60,
        "1d": 4 * 24 * 60 * 60,
        "1wk": 14 * 24 * 60 * 60,
        "1mo": 45 * 24 * 60 * 60,
    }
    threshold = max_age_seconds_by_interval.get(interval, 4 * 24 * 60 * 60)
    return "DELAYED" if age_seconds <= threshold else "STALE"


class YahooFinanceProvider:
    def __init__(self, download_fn: DownloadFn | None = None) -> None:
        self._download_fn = download_fn or self._default_download

    def fetch(self, symbol: str, *, period: str, interval: str) -> MarketDataResult:
        warnings: list[str] = []
        diagnostics: dict[str, object] = {}
        started = perf_counter()
        try:
            return self._build_result(
                self._download(symbol, period, interval),
                warnings=warnings,
                diagnostics=diagnostics,
                interval=interval,
                fetch_latency_ms=self._elapsed_ms(started),
            )
        except Exception as exc:
            diagnostics["live_error"] = str(exc)
            diagnostics["exception_type"] = exc.__class__.__name__
            if not self._is_sqlite_error(exc):
                raise

            self._disable_yfinance_cache()
            warnings.append(
                "cache-disabled-retry: yfinance sqlite cache was disabled after a provider error."
            )
            retry_df = self._download(symbol, period, interval)
            return self._build_result(
                retry_df,
                warnings=warnings,
                diagnostics=diagnostics,
                interval=interval,
                fetch_latency_ms=self._elapsed_ms(started),
            )

    def _build_result(
        self,
        df: pd.DataFrame,
        *,
        warnings: list[str],
        diagnostics: dict[str, object],
        interval: str,
        fetch_latency_ms: int,
    ) -> MarketDataResult:
        normalized = _normalize_live_frame(df)
        last_bar_time = _last_bar_time(normalized)
        return MarketDataResult(
            dataframe=normalized,
            source="live_yfinance",
            live_attempted=True,
            fallback_used=False,
            warnings=warnings,
            diagnostics=diagnostics,
            data_freshness="LIVE",
            last_bar_time=last_bar_time,
            is_stale=False,
            provider_name="YahooFinanceProvider",
            attempted_sources=["live_yfinance"],
            fetch_latency_ms=fetch_latency_ms,
            cache_hit=False,
        )

    def _download(self, symbol: str, period: str, interval: str) -> pd.DataFrame:
        return self._download_fn(symbol, period, interval)

    @staticmethod
    def _default_download(symbol: str, period: str, interval: str) -> pd.DataFrame:
        return yf.Ticker(symbol).history(period=period, interval=interval)

    @staticmethod
    def _is_sqlite_error(exc: Exception) -> bool:
        if isinstance(exc, OperationalError):
            return True
        message = str(exc).lower()
        return any(marker in message for marker in SQLITE_ERROR_MARKERS)

    @staticmethod
    def _disable_yfinance_cache() -> None:
        try:
            yf_cache._TzDBManager.close_db()
            yf_cache._CookieDBManager.close_db()
        except Exception:
            pass
        yf_cache._TzCacheManager._tz_cache = yf_cache._TzCacheDummy()
        yf_cache._CookieCacheManager._Cookie_cache = yf_cache._CookieCacheDummy()
        yf_cache._ISINCacheManager._isin_cache = yf_cache._ISINCacheDummy()

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return int((perf_counter() - started) * 1000)


class LocalCsvProvider:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self._data_dir = Path(data_dir)

    def fetch(self, symbol: str, *, period: str, interval: str) -> MarketDataResult:
        started = perf_counter()
        candidate_paths = self._candidate_paths(symbol, period, interval)
        for path in candidate_paths:
            if not path.exists():
                continue
            frame = load_csv(str(path))
            last_bar_time = _last_bar_time(frame)
            freshness = classify_freshness(last_bar_time, interval)
            return MarketDataResult(
                dataframe=frame,
                source="local_csv",
                live_attempted=False,
                fallback_used=False,
                warnings=[],
                diagnostics={"local_path": str(path)},
                data_freshness=freshness,
                last_bar_time=last_bar_time,
                is_stale=freshness in {"STALE", "UNKNOWN"},
                provider_name="LocalCsvProvider",
                attempted_sources=["local_csv"],
                fetch_latency_ms=int((perf_counter() - started) * 1000),
                cache_hit=True,
            )
        raise FileNotFoundError(f"No local CSV found for {symbol}")

    def _candidate_paths(self, symbol: str, period: str, interval: str) -> list[Path]:
        return [
            self._data_dir / f"{symbol}_{interval}_{period}.csv",
            self._data_dir / f"{symbol}_{interval}.csv",
            self._data_dir / f"{symbol}.csv",
        ]


class MarketDataService:
    def __init__(
        self,
        *,
        live_provider: YahooFinanceProvider | None = None,
        local_provider: LocalCsvProvider | None = None,
    ) -> None:
        self._live_provider = live_provider or YahooFinanceProvider()
        self._local_provider = local_provider or LocalCsvProvider()

    def fetch(self, symbol: str, *, period: str, interval: str) -> MarketDataResult:
        diagnostics: dict[str, object] = {}
        try:
            return self._live_provider.fetch(symbol, period=period, interval=interval)
        except Exception as live_exc:
            diagnostics["live_error"] = str(live_exc)

        try:
            local_result = self._local_provider.fetch(symbol, period=period, interval=interval)
            merged_diagnostics = dict(local_result.diagnostics)
            merged_diagnostics.update(diagnostics)
            return MarketDataResult(
                dataframe=local_result.dataframe,
                source=local_result.source,
                live_attempted=True,
                fallback_used=True,
                warnings=["Live data unavailable. Using local CSV fallback."],
                diagnostics=merged_diagnostics,
                data_freshness=local_result.data_freshness,
                last_bar_time=local_result.last_bar_time,
                is_stale=local_result.is_stale,
                provider_name=local_result.provider_name,
                attempted_sources=["live_yfinance", "local_csv"],
                fetch_latency_ms=local_result.fetch_latency_ms,
                cache_hit=local_result.cache_hit,
            )
        except Exception as local_exc:
            diagnostics["local_error"] = str(local_exc)
            raise ControlledMarketDataError(
                symbol=symbol,
                attempted_source="live_yfinance",
                fallback_attempted=True,
                diagnostics=diagnostics,
            ) from local_exc


def fetch_market_data(symbol: str, period: str, interval: str) -> MarketDataResult:
    return MarketDataService().fetch(symbol, period=period, interval=interval)
