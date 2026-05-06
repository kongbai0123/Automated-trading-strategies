import os
import sys
from typing import Any
from datetime import datetime

import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go

# Ensure we can import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from src.automation import generate_daily_report
from src.charting import (
    create_equity_curve,
    create_forecast_chart,
    create_price_chart,
    create_rsi_chart,
)
from src.predictor import get_ai_projection, get_investment_advice, predict_future_prices
from src.scanner import analyze_symbol_detailed
from src.storage import (
    HISTORY_FILE,
    ensure_storage,
    get_history,
    get_watchlist,
    log_access,
    remove_from_watchlist,
    save_to_watchlist,
)
from src.strategy_registry import StrategyRegistry
from src.ui_pipeline import load_config, run_backtest_pipeline

st.set_page_config(
    page_title="Trading Workspace",
    layout="wide",
    initial_sidebar_state="collapsed",
)

TIMEFRAME_OPTIONS = {
    "月K": "1mo",
    "週K": "1wk",
    "日K": "1d",
    "60 分": "60m",
    "15 分": "15m",
    "5 分": "5m",
    "1 分": "1m",
}

PERIOD_OPTIONS_BY_INTERVAL = {
    "1m": ["1d", "5d", "7d"],
    "5m": ["1d", "5d", "7d"],
    "15m": ["1d", "5d", "1mo", "3mo"],
    "60m": ["1d", "5d", "1mo", "3mo"],
}

STRATEGY_DESCRIPTIONS = {
    "RSI_MACD": "RSI + MACD 綜合策略：結合超買超賣與趨勢動能",
    "MA_CROSSOVER": "移動平均交叉策略：黃金交叉買進，死亡交叉賣出",
    "BOLLINGER_BREAKOUT": "布林通道突破策略：突破上軌買進，跌破下軌賣出",
}

CONFIG = load_config()
DEFAULT_TRANSACTION_COST = CONFIG.get("transaction_cost", 0.001)
STRATEGY_DEFAULTS = CONFIG.get("strategy_defaults", {})


def inject_css() -> None:
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Noto+Sans+TC:wght@400;500;700&display=swap');

            :root {
                --bg: #07111f;
                --panel: rgba(9, 21, 37, 0.78);
                --line: rgba(148, 163, 184, 0.18);
                --text: #e2e8f0;
                --muted: #94a3b8;
                --accent: #38bdf8;
            }

            .stApp {
                background: linear-gradient(180deg, #08111d 0%, #07111f 55%, #020617 100%);
                color: var(--text);
                font-family: 'Noto Sans TC', sans-serif;
            }

            h1, h2, h3 {
                font-family: 'Space Grotesk', 'Noto Sans TC', sans-serif !important;
            }

            .block-container {
                padding-top: 1.2rem;
                padding-bottom: 2rem;
            }

            [data-testid="stMetric"] {
                background: var(--panel);
                border: 1px solid var(--line);
                border-radius: 12px;
                padding: 0.8rem;
                backdrop-filter: blur(12px);
            }

            .stTabs [data-baseweb="tab-list"] {
                gap: 0.5rem;
            }

            .stTabs [data-baseweb="tab"] {
                background: rgba(15, 23, 42, 0.55);
                border: 1px solid var(--line);
                border-radius: 999px;
                padding: 0.4rem 0.9rem;
            }

            .stTabs [aria-selected="true"] {
                background: rgba(56, 189, 248, 0.16) !important;
                border-color: rgba(56, 189, 248, 0.45) !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    ensure_storage()
    if "symbol_input" not in st.session_state:
        st.session_state.symbol_input = "2330.TW"
    if "timeframe_label" not in st.session_state:
        st.session_state.timeframe_label = "日K"
    if "selected_strategy" not in st.session_state:
        strategies = StrategyRegistry.get_available_strategies()
        st.session_state.selected_strategy = strategies[0] if strategies else "RSI_MACD"
    if "chart_type" not in st.session_state:
        st.session_state.chart_type = "Candlestick"
    if "period" not in st.session_state:
        st.session_state.period = "2y"
    if "show_watchlist" not in st.session_state:
        st.session_state.show_watchlist = True


def current_period_options(interval: str) -> list[str]:
    return PERIOD_OPTIONS_BY_INTERVAL.get(interval, ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"])


def normalize_period(interval: str) -> None:
    period_options = current_period_options(interval)
    if st.session_state.get("period") not in period_options:
        fallback = "2y" if "2y" in period_options else period_options[min(1, len(period_options) - 1)]
        st.session_state.period = fallback


@st.cache_data(ttl=300, show_spinner=False)
def get_market_data():
    import yfinance as yf
    tickers = ["^TWII", "^IXIC", "BTC-USD", "^VIX"]
    res = {}
    try:
        df = yf.download(tickers, period="5d", progress=False)
        closes = df['Close'] if 'Close' in df.columns else df
        for t in tickers:
            if t in closes.columns:
                series = closes[t].dropna()
                if len(series) >= 2:
                    curr = float(series.iloc[-1])
                    prev = float(series.iloc[-2])
                    pct = (curr - prev) / prev
                    res[t] = {"price": curr, "change": pct}
                elif len(series) == 1:
                    res[t] = {"price": float(series.iloc[0]), "change": 0.0}
                else:
                    res[t] = {"price": 0.0, "change": 0.0}
            else:
                res[t] = {"price": 0.0, "change": 0.0}
        return res
    except Exception:
        return {t: {"price": 0.0, "change": 0.0} for t in tickers}


def render_market_status_bar() -> None:
    data = get_market_data()
    cols = st.columns([1, 1, 1, 1, 2])
    
    mapping = {
        "^TWII": "TAIEX",
        "^IXIC": "NASDAQ",
        "BTC-USD": "BTC",
        "^VIX": "VIX"
    }
    
    for i, t in enumerate(["^TWII", "^IXIC", "BTC-USD", "^VIX"]):
        d = data.get(t, {"price": 0.0, "change": 0.0})
        if t == "^VIX":
            color = "inverse" if d["change"] != 0 else "off"
        else:
            color = "normal" if d["change"] >= 0 else "inverse"
            
        cols[i].metric(mapping[t], f"{d['price']:.2f}", f"{d['change']:.2%}", delta_color=color)
    
    with cols[4]:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.markdown(f"<div style='text-align: right; color: #94a3b8; font-size: 0.95rem; margin-top: 1rem;'>Market Status<br><strong>{now_str} (TW)</strong></div>", unsafe_allow_html=True)


def render_top_controls() -> dict[str, Any]:
    st.markdown("---")
    strategies = StrategyRegistry.get_available_strategies()
    col1, col2, col3, col4, col5, col6 = st.columns([2.2, 1, 1, 1.25, 1, 0.95])

    with col1:
        symbol = st.text_input("Symbol", key="symbol_input", placeholder="例如 2330.TW 或 AAPL")
    with col2:
        timeframe_label = st.selectbox("TF", list(TIMEFRAME_OPTIONS.keys()), key="timeframe_label")
    interval = TIMEFRAME_OPTIONS[timeframe_label]
    normalize_period(interval)
    period_options = current_period_options(interval)

    with col3:
        period = st.selectbox("Period", period_options, key="period")
    with col4:
        strategy_name = st.selectbox("Strategy", strategies, key="selected_strategy")
    with col5:
        chart_type = st.selectbox("Chart", ["Candlestick", "Line", "OHLC"], key="chart_type")
    with col6:
        st.markdown("<div style='height: 1.85rem;'></div>", unsafe_allow_html=True)
        run_clicked = st.button("Run", use_container_width=True, type="primary")

    return {
        "symbol": symbol.strip(),
        "timeframe_label": timeframe_label,
        "interval": interval,
        "period": period,
        "strategy_name": strategy_name,
        "chart_type": chart_type,
        "run_clicked": run_clicked,
    }


def render_strategy_controls(strategy_name: str) -> tuple[dict[str, Any], float]:
    params: dict[str, Any] = {}
    with st.expander("策略參數設定", expanded=False):
        left, right = st.columns([2.4, 1])
        with left:
            st.caption(STRATEGY_DESCRIPTIONS.get(strategy_name, "請選擇策略"))
            if strategy_name == "RSI_MACD":
                defaults = STRATEGY_DEFAULTS.get("RSIMACDStrategy", {"overbought": 70, "oversold": 30})
                p1, p2 = st.columns(2)
                params["overbought"] = p1.slider("RSI 超買門檻", 50, 90, int(defaults.get("overbought", 70)))
                params["oversold"] = p2.slider("RSI 超賣門檻", 10, 50, int(defaults.get("oversold", 30)))
            elif strategy_name == "MA_CROSSOVER":
                defaults = STRATEGY_DEFAULTS.get("MACrossoverStrategy", {"short_col": "sma_20", "long_col": "sma_50"})
                p1, p2 = st.columns(2)
                params["short_col"] = p1.text_input("短期均線", defaults.get("short_col", "sma_20"))
                params["long_col"] = p2.text_input("長期均線", defaults.get("long_col", "sma_50"))
            elif strategy_name == "BOLLINGER_BREAKOUT":
                defaults = STRATEGY_DEFAULTS.get(
                    "BollingerBreakoutStrategy",
                    {"upper_col": "bb_upper", "lower_col": "bb_lower"},
                )
                p1, p2 = st.columns(2)
                params["upper_col"] = p1.text_input("上軌欄位", defaults.get("upper_col", "bb_upper"))
                params["lower_col"] = p2.text_input("下軌欄位", defaults.get("lower_col", "bb_lower"))
        with right:
            transaction_cost = st.number_input(
                "手續費率",
                min_value=0.0,
                max_value=0.1,
                value=float(DEFAULT_TRANSACTION_COST),
                step=0.0001,
                format="%.4f",
            )
            st.caption("台股建議 0.001425，加上回購成本約 0.003")

    return params, transaction_cost


def latest_signal_label(signal: Any) -> tuple[str, str]:
    if signal == 1:
        return "▲ 看多", "signal-buy"
    if signal == -1:
        return "▼ 看空", "signal-sell"
    return "◆ 觀望", "signal-hold"


def render_kpi_row(result: dict[str, Any]) -> None:
    kpi = result["kpi"]
    latest = result["df"].iloc[-1]
    signal_text, _ = latest_signal_label(latest.get("signal", 0))

    cols = st.columns(8)
    
    ret = kpi.get("total_return", 0)
    cols[0].metric("Total Return", f"{ret:.2%}", delta=f"{ret:.2%}", delta_color="normal")
    
    sharpe = kpi.get("sharpe", 0)
    cols[1].metric("Sharpe", f"{sharpe:.2f}")
    
    mdd = kpi.get("max_drawdown", 0)
    cols[2].metric("Max DD", f"{mdd:.2%}", delta=f"{mdd:.2%}", delta_color="normal")
    
    wr = kpi.get("win_rate", 0)
    cols[3].metric("Win Rate", f"{wr:.2%}", delta=f"{wr-0.5:.2%}", delta_color="normal")
    
    pf = kpi.get("profit_factor", 0)
    cols[4].metric("Profit Factor", f"{pf:.2f}", delta=f"{pf-1:.2f}", delta_color="normal")
    
    trades = kpi.get("total_trades", 0)
    cols[5].metric("Trades", f"{trades}")
    
    exp = kpi.get("exposure", 0)
    cols[6].metric("Exposure", f"{exp:.2%}")
    
    cols[7].metric("Signal", signal_text)


def create_macd_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if 'macd' not in df.columns: return fig
    
    colors = ['#10b981' if val >= 0 else '#f43f5e' for val in df['macd_hist']]
    fig.add_trace(go.Bar(x=df.index, y=df['macd_hist'], name='Hist', marker_color=colors, opacity=0.7))
    fig.add_trace(go.Scatter(x=df.index, y=df['macd'], mode='lines', name='MACD', line=dict(color='#3b82f6')))
    fig.add_trace(go.Scatter(x=df.index, y=df['macd_signal'], mode='lines', name='Signal', line=dict(color='#fbbf24')))
    
    fig.update_layout(
        title=dict(text="MACD 指標", font=dict(size=16, color='white')),
        template="plotly_dark",
        height=300,
        margin=dict(l=40, r=40, t=40, b=40),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(gridcolor='rgba(255, 255, 255, 0.05)'),
        yaxis=dict(gridcolor='rgba(255, 255, 255, 0.05)')
    )
    return fig


def render_analysis_tab(result: dict[str, Any], chart_type: str) -> None:
    df = result["df"]
    metadata = result["metadata"]
    
    title = f"{metadata['symbol']}  |  {metadata['interval']}  |  {metadata['strategy_name']}"
    st.plotly_chart(create_price_chart(df, title=title, chart_type=chart_type), use_container_width=True)
    
    c1, c2 = st.columns(2)
    with c1:
        if metadata["strategy_name"] == "RSI_MACD":
            overbought = metadata["parameters"].get("overbought", 70)
            oversold = metadata["parameters"].get("oversold", 30)
            st.plotly_chart(create_rsi_chart(df, overbought, oversold), use_container_width=True)
        else:
            st.plotly_chart(create_rsi_chart(df), use_container_width=True)
    with c2:
        st.plotly_chart(create_macd_chart(df), use_container_width=True)


def render_backtest_tab(result: dict[str, Any]) -> None:
    df = result["df"]
    st.markdown("### 資產曲線")
    
    fig = create_equity_curve(df)
    if "returns" in df.columns:
        bh_equity = (1 + df["returns"]).cumprod()
        fig.add_trace(go.Scatter(
            x=df.index, y=bh_equity,
            mode='lines', name='Buy & Hold',
            line=dict(color='gray', dash='dash')
        ))
    st.plotly_chart(fig, use_container_width=True)
    
    display_cols = ["open", "high", "low", "close", "signal", "position", "strategy_returns", "equity"]
    existing_cols = [col for col in display_cols if col in df.columns]
    st.markdown("### 最近交易明細")
    st.dataframe(df[existing_cols].tail(30), use_container_width=True, height=420)


def render_ai_tab(result: dict[str, Any]) -> None:
    df = result["df"]
    projection = get_ai_projection(df)
    advice = get_investment_advice(df)
    scenarios = projection.get("scenarios", {})
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Trend Score", f"{projection['trend_score']:.0f}")
    c2.metric("Risk Score", f"{projection['risk_score']:.0f}")
    c3.metric("AI Stance", projection["sentiment"])

    st.markdown("---")
    left, right = st.columns(2)
    with left:
        st.markdown("#### Decision Notes")
        st.info(f"**{advice['advice']}**")
        for reason in advice['reasons']:
            st.write(f"- {reason}")
            
        st.markdown("#### Risk Radar")
        st.warning(projection['risk_reason'])
        
    with right:
        st.markdown("#### 未來 10 日情境")
        if scenarios:
            st.write(f"- 🟢 樂觀：{scenarios['bullish']:.2f}")
            st.write(f"- ⚪ 中性：{scenarios['neutral_lower']:.2f} ~ {scenarios['neutral_upper']:.2f}")
            st.write(f"- 🔴 悲觀：{scenarios['bearish']:.2f}")
        else:
            st.info("資料不足，無法計算情境。")
            
        forecast_df = predict_future_prices(df)
        if not forecast_df.empty:
            st.plotly_chart(create_forecast_chart(df, forecast_df), use_container_width=True)


def run_screener(symbols: list[str], strategy_name: str, params: dict[str, Any], tc: float, period: str, interval: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    progress = st.progress(0)
    placeholder = st.empty()

    for idx, symbol in enumerate(symbols, start=1):
        try:
            result = run_backtest_pipeline(symbol, strategy_name, params, tc, period, interval)
            analysis = analyze_symbol_detailed(result["df"], symbol=symbol)
            latest = result["df"].iloc[-1]
            signal, _ = latest_signal_label(latest.get("signal", 0))
            rows.append(
                {
                    "Symbol": symbol,
                    "Score": analysis["score"],
                    "Trend": analysis["trend"],
                    "Signal": signal,
                    "Risk": analysis["risk"],
                    "Volume Ratio": f"{analysis['volume_ratio']:.1f}x",
                    "Return": f"{result['kpi']['total_return']:.2%}",
                    "Reason": analysis["reason"],
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "Symbol": symbol,
                    "Score": 0,
                    "Trend": "Error",
                    "Signal": "-",
                    "Risk": "-",
                    "Volume Ratio": "-",
                    "Return": "-",
                    "Reason": str(exc),
                }
            )
        progress.progress(idx / len(symbols))
        placeholder.dataframe(pd.DataFrame(rows), use_container_width=True, height=360)

    return pd.DataFrame(rows)


def render_scanner_tab(strategy_name: str, params: dict[str, Any], tc: float, interval: str) -> None:
    st.markdown("### Scanner")
    default_symbols = "2330.TW, 2317.TW, 2454.TW, 2382.TW, 2881.TW"
    symbol_text = st.text_area("掃描清單", value=default_symbols, height=100)
    scan_period = st.selectbox("掃描區間", ["1mo", "3mo", "6mo", "1y"], index=1, key="scanner_period")
    if st.button("開始掃描", use_container_width=True):
        symbols = [item.strip() for item in symbol_text.split(",") if item.strip()]
        if symbols:
            with st.spinner("掃描中..."):
                result_df = run_screener(symbols, strategy_name, params, tc, scan_period, interval)
            st.success(f"掃描完成！共分析 {len(result_df)} 個標的。")


def render_watchlist_panel(symbol: str):
    if not st.session_state.show_watchlist:
        if st.button("▶", help="展開 Watchlist"):
            st.session_state.show_watchlist = True
            st.rerun()
        return

    c1, c2 = st.columns([3, 1])
    c1.markdown("### ⭐ Watchlist")
    if c2.button("◀", help="收起"):
        st.session_state.show_watchlist = False
        st.rerun()

    watchlist = get_watchlist()
    if symbol:
        if symbol in watchlist:
            if st.button(f"❌ 移除 {symbol}", use_container_width=True):
                remove_from_watchlist(symbol)
                st.rerun()
        else:
            if st.button(f"⭐ 加入 {symbol}", use_container_width=True):
                save_to_watchlist(symbol)
                st.rerun()

    st.markdown("---")
    if watchlist:
        for item in watchlist:
            btn_type = "primary" if item == symbol else "secondary"
            if st.button(item, key=f"wl_{item}", use_container_width=True, type=btn_type):
                st.session_state.symbol_input = item
                st.rerun()
    else:
        st.info("清單為空")


def render_sidebar(symbol: str, strategy_name: str, interval: str) -> None:
    with st.sidebar:
        st.markdown("## Sidebar Tools")
        st.markdown("### Daily Report")
        watchlist = get_watchlist()
        if st.button("產生每日報告", use_container_width=True):
            targets = watchlist if watchlist else ([symbol] if symbol else [])
            if not targets:
                st.warning("請先加入標的至 watchlist。")
            else:
                with st.spinner("產生報告中..."):
                    report_path = generate_daily_report(targets, strategy_name, interval)
                if report_path:
                    st.success(f"報告已產出：{report_path}")
                else:
                    st.error("報告產出失敗。")

        st.markdown("### Recent History")
        history = get_history(8)
        if not history.empty:
            st.dataframe(history, use_container_width=True, height=240)
            if st.button("清除紀錄", use_container_width=True):
                pd.DataFrame(columns=["timestamp", "symbol", "interval", "score", "sentiment"]).to_csv(HISTORY_FILE, index=False)
                st.rerun()


def execute_analysis(symbol: str, strategy_name: str, params: dict[str, Any], tc: float, period: str, interval: str, chart_type: str) -> None:
    if not symbol:
        st.error("請輸入股票代碼後再執行分析。")
        return

    with st.spinner(f"正在抓取並分析 {symbol}..."):
        result = run_backtest_pipeline(symbol, strategy_name, params, tc, period, interval)
    st.session_state.latest_result = result
    st.session_state.last_chart_type = chart_type

    projection = get_ai_projection(result["df"])
    log_access(symbol, interval, int(projection["trend_score"]), projection["sentiment"])


def main() -> None:
    init_state()
    inject_css()
    
    render_market_status_bar()
    
    control_state = render_top_controls()
    strategy_params, transaction_cost = render_strategy_controls(control_state["strategy_name"])
    render_sidebar(control_state["symbol"], control_state["strategy_name"], control_state["interval"])

    if control_state["run_clicked"]:
        try:
            execute_analysis(
                control_state["symbol"],
                control_state["strategy_name"],
                strategy_params,
                transaction_cost,
                control_state["period"],
                control_state["interval"],
                control_state["chart_type"],
            )
        except Exception as exc:
            st.error(f"分析失敗：{exc}")

    if st.session_state.show_watchlist:
        left_col, right_col = st.columns([1, 4.5])
    else:
        left_col, right_col = st.columns([0.1, 4.5])
        
    with left_col:
        render_watchlist_panel(control_state["symbol"])
        
    with right_col:
        latest_result = st.session_state.get("latest_result")
        chart_type = st.session_state.get("last_chart_type", control_state["chart_type"])

        if latest_result:
            render_kpi_row(latest_result)
            render_analysis_tab(latest_result, chart_type)
            
            tabs = st.tabs(["📈 回測", "🔍 Scanner", "🤖 AI Projection", "📦 匯出"])
            with tabs[0]:
                render_backtest_tab(latest_result)
            with tabs[1]:
                render_scanner_tab(
                    control_state["strategy_name"],
                    strategy_params,
                    transaction_cost,
                    control_state["interval"],
                )
            with tabs[2]:
                render_ai_tab(latest_result)
            with tabs[3]:
                df = latest_result["df"]
                csv = df.to_csv(index=True).encode('utf-8')
                st.download_button("下載資料 CSV", csv, "data.csv", "text/csv")
        else:
            st.info("請點擊上方 Run 按鈕開始分析，結果將顯示於此頁。")


if __name__ == "__main__":
    main()
