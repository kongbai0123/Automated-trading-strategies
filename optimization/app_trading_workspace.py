# app.py
# -*- coding: utf-8 -*-
"""
Professional Streamlit trading dashboard for Automated-trading-strategies.

Design intent:
- UI is only orchestration. Core calculations remain in src modules.
- Main controls are moved to a top control bar to preserve chart workspace.
- Sidebar is collapsed by default and used only for secondary utilities.
- Data flow:
    fetch/load data -> add indicators -> generate signal -> backtest -> KPI -> charts/tables

Expected existing project modules:
src/
  data_loader.py       load_csv(filepath)
  indicators.py        add_indicators(df), calculate_sma(...)
  strategies.py        RSIMACDStrategy, MACrossoverStrategy
  backtest.py          BacktestEngine
  analytics.py         calculate_kpi(df)

Run:
    streamlit run app.py
"""

from __future__ import annotations

import io
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots


# -----------------------------------------------------------------------------
# Path / Imports
# -----------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"
CONFIG_DIR = PROJECT_ROOT / "configs"

for p in [SRC_DIR, DATA_DIR, REPORTS_DIR, CONFIG_DIR]:
    p.mkdir(parents=True, exist_ok=True)

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from data_loader import load_csv
    from indicators import add_indicators, calculate_sma
    from strategies import RSIMACDStrategy, MACrossoverStrategy
    from backtest import BacktestEngine
    from analytics import calculate_kpi
except Exception as import_error:
    st.set_page_config(page_title="Trading Dashboard", layout="wide")
    st.error("核心模組載入失敗。請確認 app.py 位於專案根目錄，且 src/ 內含 data_loader、indicators、strategies、backtest、analytics。")
    st.exception(import_error)
    st.stop()


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class DashboardConfig:
    symbol: str = "2330.TW"
    period: str = "2y"
    timeframe: str = "1d"
    strategy_name: str = "RSI_MACD"
    transaction_cost: float = 0.001
    rsi_overbought: int = 70
    rsi_oversold: int = 30
    ma_short_col: str = "sma_20"
    ma_long_col: str = "sma_50"
    use_cache: bool = True


TIMEFRAME_OPTIONS: Dict[str, str] = {
    "1分": "1m",
    "5分": "5m",
    "15分": "15m",
    "30分": "30m",
    "60分": "60m",
    "日K": "1d",
    "週K": "1wk",
    "月K": "1mo",
}

PERIOD_OPTIONS: List[str] = ["5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y"]
STRATEGY_OPTIONS: List[str] = ["RSI_MACD", "MA_CROSSOVER"]


def load_ui_config() -> DashboardConfig:
    config_path = CONFIG_DIR / "ui_config.json"
    if not config_path.exists():
        return DashboardConfig()

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        return DashboardConfig(**{**asdict(DashboardConfig()), **raw})
    except Exception:
        return DashboardConfig()


def save_ui_config(config: DashboardConfig) -> None:
    config_path = CONFIG_DIR / "ui_config.json"
    config_path.write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")


# -----------------------------------------------------------------------------
# Data access
# -----------------------------------------------------------------------------

def data_file_path(symbol: str, period: str, timeframe: str) -> Path:
    safe_symbol = symbol.replace("/", "_").replace("\\", "_")
    return DATA_DIR / f"{safe_symbol}_{timeframe}_{period}.csv"


def normalize_yfinance_frame(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Normalize yfinance output to Date/Open/High/Low/Close/Volume for existing load_csv()."""
    if df is None or df.empty:
        raise ValueError(f"No market data returned for {symbol}")

    out = df.copy()

    if isinstance(out.columns, pd.MultiIndex):
        level0 = [str(c[0]).strip() for c in out.columns]
        level1 = [str(c[1]).strip() for c in out.columns]
        if symbol in level1:
            keep = [i for i, s in enumerate(level1) if s == symbol]
            out = out.iloc[:, keep].copy()
            out.columns = [level0[i] for i in keep]
        else:
            out.columns = level0

    if isinstance(out.index, pd.DatetimeIndex) and out.index.tz is not None:
        out.index = out.index.tz_convert(None)

    out = out.reset_index()
    if "Datetime" in out.columns and "Date" not in out.columns:
        out = out.rename(columns={"Datetime": "Date"})
    if "timestamp" in out.columns and "Date" not in out.columns:
        out = out.rename(columns={"timestamp": "Date"})

    required = ["Date", "Open", "High", "Low", "Close", "Volume"]
    missing = [c for c in required if c not in out.columns]
    if missing:
        raise ValueError(f"yfinance 資料缺少欄位：{missing}")

    return out[required].copy()


@st.cache_data(show_spinner=False)
def fetch_yfinance_cached(symbol: str, period: str, timeframe: str) -> pd.DataFrame:
    import yfinance as yf

    return yf.download(symbol, period=period, interval=timeframe, auto_adjust=False, progress=False)


def fetch_and_store_market_data(symbol: str, period: str, timeframe: str, use_cache: bool) -> Path:
    if use_cache:
        raw = fetch_yfinance_cached(symbol, period, timeframe)
    else:
        import yfinance as yf
        raw = yf.download(symbol, period=period, interval=timeframe, auto_adjust=False, progress=False)

    normalized = normalize_yfinance_frame(raw, symbol)
    path = data_file_path(symbol, period, timeframe)
    normalized.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def load_market_data(path: Path) -> pd.DataFrame:
    df = load_csv(str(path))
    required = {"open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"資料缺少必要欄位：{missing}")
    return df


# -----------------------------------------------------------------------------
# Pipeline
# -----------------------------------------------------------------------------

def ensure_strategy_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Patch derived columns needed by selected strategies without modifying source df."""
    out = df.copy()
    if "sma_50" not in out.columns:
        out["sma_50"] = calculate_sma(out["close"], 50)
    return out


def build_strategy(config: DashboardConfig):
    if config.strategy_name == "RSI_MACD":
        return RSIMACDStrategy(
            rsi_col="rsi_14",
            macd_hist_col="macd_hist",
            overbought=config.rsi_overbought,
            oversold=config.rsi_oversold,
        )

    if config.strategy_name == "MA_CROSSOVER":
        return MACrossoverStrategy(
            short_col=config.ma_short_col,
            long_col=config.ma_long_col,
        )

    raise ValueError(f"Unsupported strategy: {config.strategy_name}")


def run_analysis_pipeline(data_path: Path, config: DashboardConfig) -> Tuple[pd.DataFrame, Dict[str, float], Dict[str, object]]:
    base_df = load_market_data(data_path)
    indicator_df = add_indicators(base_df)
    indicator_df = ensure_strategy_columns(indicator_df)

    strategy = build_strategy(config)
    signals = strategy.generate_signals(indicator_df)

    analysis_df = indicator_df.copy()
    analysis_df["signal"] = signals

    engine = BacktestEngine(transaction_cost=config.transaction_cost)
    result_df = engine.run(analysis_df)

    kpi = calculate_kpi(result_df)
    metadata = {
        "dataset_file": str(data_path),
        "symbol": config.symbol,
        "period": config.period,
        "timeframe": config.timeframe,
        "strategy_name": config.strategy_name,
        "transaction_cost": config.transaction_cost,
        "rsi_overbought": config.rsi_overbought,
        "rsi_oversold": config.rsi_oversold,
        "ma_short_col": config.ma_short_col,
        "ma_long_col": config.ma_long_col,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }

    return result_df, kpi, metadata


# -----------------------------------------------------------------------------
# Charting
# -----------------------------------------------------------------------------

def build_price_chart(df: pd.DataFrame, chart_type: str = "Candlestick") -> go.Figure:
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.03,
        specs=[[{"secondary_y": False}], [{"secondary_y": False}]],
    )

    if chart_type == "Candlestick":
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name="K線",
                increasing_line_color="#00c176",
                decreasing_line_color="#ff4d4f",
            ),
            row=1,
            col=1,
        )
    else:
        fig.add_trace(go.Scatter(x=df.index, y=df["close"], mode="lines", name="Close"), row=1, col=1)

    overlays = {
        "sma_20": ("SMA 20", "#4ea1ff"),
        "sma_50": ("SMA 50", "#ffa940"),
        "ema_20": ("EMA 20", "#b37feb"),
    }

    for col, (label, color) in overlays.items():
        if col in df.columns:
            fig.add_trace(
                go.Scatter(x=df.index, y=df[col], mode="lines", name=label, line=dict(width=1.5, color=color)),
                row=1,
                col=1,
            )

    buy_df = df[df.get("signal", 0) == 1]
    sell_df = df[df.get("signal", 0) == -1]

    if not buy_df.empty:
        fig.add_trace(
            go.Scatter(
                x=buy_df.index,
                y=buy_df["close"],
                mode="markers",
                name="Buy",
                marker=dict(symbol="triangle-up", size=12, color="#00c176"),
            ),
            row=1,
            col=1,
        )

    if not sell_df.empty:
        fig.add_trace(
            go.Scatter(
                x=sell_df.index,
                y=sell_df["close"],
                mode="markers",
                name="Sell",
                marker=dict(symbol="triangle-down", size=12, color="#ff4d4f"),
            ),
            row=1,
            col=1,
        )

    volume_colors = np.where(df["close"] >= df["open"], "#00c176", "#ff4d4f")
    fig.add_trace(
        go.Bar(x=df.index, y=df["volume"], name="Volume", marker_color=volume_colors, opacity=0.45),
        row=2,
        col=1,
    )

    fig.update_layout(
        height=720,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(8,13,23,0.95)",
        margin=dict(l=20, r=20, t=35, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
    )

    fig.update_yaxes(gridcolor="rgba(255,255,255,0.08)")
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.05)")
    return fig


def build_rsi_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if "rsi_14" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["rsi_14"], mode="lines", name="RSI 14", line=dict(color="#4ea1ff")))
        fig.add_hline(y=70, line_dash="dash", line_color="#ff4d4f")
        fig.add_hline(y=30, line_dash="dash", line_color="#00c176")

    fig.update_layout(
        height=280,
        template="plotly_dark",
        margin=dict(l=20, r=20, t=30, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(8,13,23,0.95)",
        yaxis=dict(range=[0, 100]),
    )
    return fig


def build_macd_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if {"macd", "macd_signal", "macd_hist"}.issubset(df.columns):
        colors = np.where(df["macd_hist"] >= 0, "#00c176", "#ff4d4f")
        fig.add_trace(go.Bar(x=df.index, y=df["macd_hist"], name="Hist", marker_color=colors, opacity=0.55))
        fig.add_trace(go.Scatter(x=df.index, y=df["macd"], name="MACD", line=dict(color="#4ea1ff")))
        fig.add_trace(go.Scatter(x=df.index, y=df["macd_signal"], name="Signal", line=dict(color="#ffa940")))

    fig.update_layout(
        height=280,
        template="plotly_dark",
        margin=dict(l=20, r=20, t=30, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(8,13,23,0.95)",
        hovermode="x unified",
    )
    return fig


def build_equity_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if "equity" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["equity"],
                mode="lines",
                name="Equity",
                fill="tozeroy",
                line=dict(color="#00c176", width=2),
            )
        )

    fig.update_layout(
        height=420,
        template="plotly_dark",
        margin=dict(l=20, r=20, t=30, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(8,13,23,0.95)",
        hovermode="x unified",
    )
    return fig


# -----------------------------------------------------------------------------
# UI helpers
# -----------------------------------------------------------------------------

def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.1rem;
            padding-bottom: 2rem;
            max-width: 96vw;
        }

        [data-testid="stSidebar"] {
            min-width: 270px;
            max-width: 270px;
        }

        .dashboard-title {
            font-size: 2.2rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            margin-bottom: 0.1rem;
        }

        .dashboard-subtitle {
            color: #9aa4b2;
            font-size: 0.95rem;
            margin-bottom: 1rem;
        }

        .glass-panel {
            border: 1px solid rgba(255,255,255,0.08);
            background: linear-gradient(135deg, rgba(17,24,39,0.92), rgba(15,23,42,0.75));
            border-radius: 18px;
            padding: 1rem 1.1rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.22);
        }

        .kpi-card {
            border: 1px solid rgba(255,255,255,0.08);
            background: rgba(15,23,42,0.85);
            border-radius: 16px;
            padding: 1rem;
            min-height: 105px;
        }

        .kpi-label {
            color: #9aa4b2;
            font-size: 0.82rem;
        }

        .kpi-value {
            font-size: 1.65rem;
            font-weight: 800;
            margin-top: 0.25rem;
        }

        .kpi-note {
            color: #64748b;
            font-size: 0.78rem;
            margin-top: 0.2rem;
        }

        div[data-testid="stMetric"] {
            background: rgba(15,23,42,0.82);
            border: 1px solid rgba(255,255,255,0.08);
            padding: 1rem;
            border-radius: 16px;
        }

        .stButton > button {
            width: 100%;
            border-radius: 12px;
            height: 2.8rem;
            font-weight: 700;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_cards(kpi: Dict[str, float], df: pd.DataFrame) -> None:
    total_return = kpi.get("total_return", np.nan)
    sharpe = kpi.get("sharpe", np.nan)
    mdd = kpi.get("max_drawdown", np.nan)

    latest_close = float(df["close"].iloc[-1]) if not df.empty else np.nan
    latest_signal = int(df["signal"].iloc[-1]) if "signal" in df.columns and not df.empty else 0
    signal_text = {1: "BUY", -1: "SELL", 0: "HOLD"}.get(latest_signal, "HOLD")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Return", f"{total_return:.2%}" if pd.notna(total_return) else "N/A")
    c2.metric("Sharpe", f"{sharpe:.2f}" if pd.notna(sharpe) else "N/A")
    c3.metric("Max Drawdown", f"{mdd:.2%}" if pd.notna(mdd) else "N/A")
    c4.metric("Latest Signal", signal_text, f"Close {latest_close:,.2f}" if pd.notna(latest_close) else "")


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    export = df.copy()
    if isinstance(export.index, pd.DatetimeIndex):
        export.insert(0, "timestamp", export.index)
    return export.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")


def render_metadata(metadata: Dict[str, object]) -> None:
    with st.expander("回測 metadata / Traceability", expanded=False):
        st.json(metadata)


def get_existing_data_files() -> List[Path]:
    return sorted(DATA_DIR.glob("*.csv"))


def render_sidebar() -> None:
    st.sidebar.title("📌 工作台")
    st.sidebar.caption("Sidebar 僅保留次要資訊，主要操作集中在上方控制列。")

    files = get_existing_data_files()
    st.sidebar.subheader("資料檔")
    if files:
        for f in files[-8:]:
            st.sidebar.write(f"• {f.name}")
    else:
        st.sidebar.info("data/ 尚無 CSV")

    st.sidebar.subheader("操作建議")
    st.sidebar.markdown(
        """
        1. 選擇標的與週期  
        2. 點擊開始分析  
        3. 看主圖與 KPI  
        4. 再看回測與訊號表  
        """
    )


def render_top_controls(defaults: DashboardConfig) -> DashboardConfig:
    with st.container():
        c1, c2, c3, c4, c5, c6 = st.columns([2.2, 1.1, 1.1, 1.25, 1.2, 1.15])

        with c1:
            symbol = st.text_input("標的代碼", value=defaults.symbol, placeholder="例如 2330.TW, AAPL, TSLA")

        with c2:
            timeframe_label = st.selectbox(
                "週期",
                list(TIMEFRAME_OPTIONS.keys()),
                index=list(TIMEFRAME_OPTIONS.values()).index(defaults.timeframe)
                if defaults.timeframe in TIMEFRAME_OPTIONS.values()
                else 5,
            )
            timeframe = TIMEFRAME_OPTIONS[timeframe_label]

        with c3:
            period = st.selectbox(
                "區間",
                PERIOD_OPTIONS,
                index=PERIOD_OPTIONS.index(defaults.period) if defaults.period in PERIOD_OPTIONS else 5,
            )

        with c4:
            strategy_name = st.selectbox(
                "策略",
                STRATEGY_OPTIONS,
                index=STRATEGY_OPTIONS.index(defaults.strategy_name)
                if defaults.strategy_name in STRATEGY_OPTIONS
                else 0,
            )

        with c5:
            chart_type = st.selectbox("圖表", ["Candlestick", "Line"], index=0)

        with c6:
            st.write("")
            run_button = st.button("🚀 開始分析", type="primary", use_container_width=True)

    with st.expander("⚙️ 進階參數", expanded=False):
        p1, p2, p3, p4, p5 = st.columns(5)
        transaction_cost = p1.number_input(
            "交易成本",
            min_value=0.0,
            max_value=0.05,
            value=float(defaults.transaction_cost),
            step=0.0005,
            format="%.4f",
        )
        rsi_overbought = p2.slider("RSI 超買", 50, 95, int(defaults.rsi_overbought), 1)
        rsi_oversold = p3.slider("RSI 超賣", 5, 50, int(defaults.rsi_oversold), 1)
        ma_short_col = p4.selectbox("短均線", ["sma_20", "ema_20"], index=0)
        ma_long_col = p5.selectbox("長均線", ["sma_50", "sma_20"], index=0)
        use_cache = st.checkbox("使用快取資料下載", value=defaults.use_cache)

    config = DashboardConfig(
        symbol=symbol.strip(),
        period=period,
        timeframe=timeframe,
        strategy_name=strategy_name,
        transaction_cost=transaction_cost,
        rsi_overbought=rsi_overbought,
        rsi_oversold=rsi_oversold,
        ma_short_col=ma_short_col,
        ma_long_col=ma_long_col,
        use_cache=use_cache,
    )

    st.session_state["chart_type"] = chart_type
    st.session_state["run_button"] = run_button
    return config


# -----------------------------------------------------------------------------
# Pages
# -----------------------------------------------------------------------------

def render_analysis_tab(df: pd.DataFrame) -> None:
    st.plotly_chart(build_price_chart(df, st.session_state.get("chart_type", "Candlestick")), use_container_width=True)

    lower_left, lower_right = st.columns(2)
    with lower_left:
        st.subheader("RSI")
        st.plotly_chart(build_rsi_chart(df), use_container_width=True)
    with lower_right:
        st.subheader("MACD")
        st.plotly_chart(build_macd_chart(df), use_container_width=True)


def render_backtest_tab(df: pd.DataFrame, kpi: Dict[str, float]) -> None:
    st.subheader("Equity Curve")
    st.plotly_chart(build_equity_chart(df), use_container_width=True)

    st.subheader("績效摘要")
    render_kpi_cards(kpi, df)

    st.subheader("最近 30 筆回測資料")
    cols = [c for c in ["close", "signal", "position", "returns", "strategy_returns", "cost", "equity"] if c in df.columns]
    st.dataframe(df[cols].tail(30), use_container_width=True)


def render_signal_tab(df: pd.DataFrame) -> None:
    st.subheader("交易訊號")
    signal_rows = df[df["signal"] != 0].copy() if "signal" in df.columns else pd.DataFrame()
    if signal_rows.empty:
        st.info("目前區間內沒有觸發買賣訊號。")
        return

    cols = [c for c in ["close", "rsi_14", "macd_hist", "signal", "position", "equity"] if c in signal_rows.columns]
    st.dataframe(signal_rows[cols].tail(100), use_container_width=True)


def render_scanner_tab(config: DashboardConfig) -> None:
    st.subheader("多標的 Scanner（MVP）")
    st.caption("輸入多個 symbol，以逗號分隔。系統會用相同週期與策略掃描最新訊號。")

    symbols_text = st.text_area("Symbols", value="2330.TW,2317.TW,2454.TW,AAPL,TSLA", height=90)
    scan = st.button("🔍 執行掃描", use_container_width=False)

    if not scan:
        return

    rows: List[Dict[str, object]] = []
    symbols = [s.strip() for s in symbols_text.split(",") if s.strip()]

    progress = st.progress(0)
    for i, sym in enumerate(symbols):
        try:
            local_config = DashboardConfig(**{**asdict(config), "symbol": sym})
            path = fetch_and_store_market_data(sym, local_config.period, local_config.timeframe, local_config.use_cache)
            df, kpi, _ = run_analysis_pipeline(path, local_config)
            latest = df.iloc[-1]
            rows.append(
                {
                    "symbol": sym,
                    "signal": int(latest.get("signal", 0)),
                    "close": float(latest["close"]),
                    "rsi_14": float(latest.get("rsi_14", np.nan)),
                    "macd_hist": float(latest.get("macd_hist", np.nan)),
                    "total_return": float(kpi.get("total_return", np.nan)),
                    "sharpe": float(kpi.get("sharpe", np.nan)),
                    "max_drawdown": float(kpi.get("max_drawdown", np.nan)),
                }
            )
        except Exception as e:
            rows.append({"symbol": sym, "error": str(e)})

        progress.progress((i + 1) / max(len(symbols), 1))

    result = pd.DataFrame(rows)
    if "signal" in result.columns:
        result = result.sort_values(["signal", "sharpe"], ascending=[False, False], na_position="last")

    st.dataframe(result, use_container_width=True)

    st.download_button(
        "下載 Scanner CSV",
        data=result.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
        file_name=f"scanner_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )


def render_ai_projection_tab(df: pd.DataFrame) -> None:
    st.subheader("AI Projection / 情境推演（規則型 MVP）")
    st.caption("此區不做『保證預測』，只提供趨勢、風險與波動情境。")

    if df.empty:
        st.warning("沒有資料可推演。")
        return

    latest = df.iloc[-1]
    trend_score = 50
    reasons: List[str] = []

    if latest.get("close", np.nan) > latest.get("sma_20", np.inf):
        trend_score += 15
        reasons.append("收盤價高於 SMA20")
    else:
        trend_score -= 10
        reasons.append("收盤價低於 SMA20")

    if latest.get("sma_20", np.nan) > latest.get("sma_50", np.inf):
        trend_score += 15
        reasons.append("SMA20 高於 SMA50")
    else:
        trend_score -= 10
        reasons.append("SMA20 未高於 SMA50")

    rsi = latest.get("rsi_14", np.nan)
    if pd.notna(rsi):
        if 40 <= rsi <= 65:
            trend_score += 10
            reasons.append("RSI 位於較健康區間")
        elif rsi > 75:
            trend_score -= 15
            reasons.append("RSI 過熱")
        elif rsi < 30:
            trend_score -= 5
            reasons.append("RSI 超賣，需等待反轉確認")

    trend_score = int(max(0, min(100, trend_score)))
    risk_score = int(min(100, max(0, abs(float(latest.get("returns", 0))) * 1000))) if "returns" in df.columns else 50

    c1, c2, c3 = st.columns(3)
    c1.metric("Trend Score", f"{trend_score}/100")
    c2.metric("Risk Score", f"{risk_score}/100")
    c3.metric("Scenario", "Bullish" if trend_score >= 65 else "Neutral" if trend_score >= 40 else "Bearish")

    st.markdown("#### 推演依據")
    for r in reasons:
        st.write(f"• {r}")


# -----------------------------------------------------------------------------
# Main app
# -----------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title="專業量化交易分析系統",
        page_icon="💡",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_styles()
    render_sidebar()

    defaults = load_ui_config()

    st.markdown('<div class="dashboard-title">💡 專業量化交易分析工作台</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="dashboard-subtitle">看盤優先、參數次之。資料 → 指標 → 策略 → 回測 → 掃描 → 情境推演。</div>',
        unsafe_allow_html=True,
    )

    config = render_top_controls(defaults)

    if st.session_state.get("run_button"):
        save_ui_config(config)

        with st.spinner("下載資料、計算指標、產生訊號與回測中..."):
            try:
                path = fetch_and_store_market_data(config.symbol, config.period, config.timeframe, config.use_cache)
                df, kpi, metadata = run_analysis_pipeline(path, config)
                st.session_state["analysis_df"] = df
                st.session_state["kpi"] = kpi
                st.session_state["metadata"] = metadata
            except Exception as e:
                st.error("分析流程失敗。請檢查 symbol、週期、網路或資料欄位。")
                st.exception(e)
                st.stop()

    if "analysis_df" not in st.session_state:
        st.info("請在上方設定參數，並點擊「開始分析」。")
        return

    df: pd.DataFrame = st.session_state["analysis_df"]
    kpi: Dict[str, float] = st.session_state["kpi"]
    metadata: Dict[str, object] = st.session_state["metadata"]

    render_kpi_cards(kpi, df)

    tab_analysis, tab_backtest, tab_signals, tab_scanner, tab_ai, tab_export = st.tabs(
        ["📊 看盤分析", "📈 策略回測", "🚦 交易訊號", "🔍 Scanner", "🤖 Projection", "📦 匯出"]
    )

    with tab_analysis:
        render_analysis_tab(df)

    with tab_backtest:
        render_backtest_tab(df, kpi)

    with tab_signals:
        render_signal_tab(df)

    with tab_scanner:
        render_scanner_tab(config)

    with tab_ai:
        render_ai_projection_tab(df)

    with tab_export:
        st.subheader("匯出")
        st.download_button(
            "下載完整分析結果 CSV",
            data=dataframe_to_csv_bytes(df),
            file_name=f"{config.symbol}_{config.timeframe}_{config.period}_analysis.csv",
            mime="text/csv",
            use_container_width=True,
        )

        metadata_json = json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8")
        st.download_button(
            "下載 metadata JSON",
            data=metadata_json,
            file_name=f"{config.symbol}_{config.timeframe}_{config.period}_metadata.json",
            mime="application/json",
            use_container_width=True,
        )

        render_metadata(metadata)


if __name__ == "__main__":
    main()
