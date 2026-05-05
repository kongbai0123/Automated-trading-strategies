import os
import sys
from typing import Any

import pandas as pd
import streamlit as st

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
                --panel-strong: rgba(12, 29, 49, 0.92);
                --line: rgba(148, 163, 184, 0.18);
                --text: #e2e8f0;
                --muted: #94a3b8;
                --accent: #38bdf8;
                --up: #22c55e;
                --down: #fb7185;
                --warning: #f59e0b;
            }

            .stApp {
                background:
                    radial-gradient(circle at top left, rgba(56, 189, 248, 0.16), transparent 28%),
                    radial-gradient(circle at top right, rgba(34, 197, 94, 0.12), transparent 22%),
                    linear-gradient(180deg, #08111d 0%, #07111f 55%, #020617 100%);
                color: var(--text);
                font-family: 'Noto Sans TC', sans-serif;
            }

            h1, h2, h3, .workspace-title, .workspace-kicker {
                font-family: 'Space Grotesk', 'Noto Sans TC', sans-serif !important;
            }

            .block-container {
                padding-top: 1.2rem;
                padding-bottom: 2rem;
            }

            [data-testid="stSidebar"] {
                background: rgba(7, 17, 31, 0.96);
                border-right: 1px solid var(--line);
            }

            [data-testid="stMetric"] {
                background: var(--panel);
                border: 1px solid var(--line);
                border-radius: 18px;
                padding: 0.9rem 1rem;
                backdrop-filter: blur(12px);
            }

            [data-testid="stMetricLabel"] {
                color: var(--muted);
            }

            .workspace-shell {
                background: linear-gradient(180deg, rgba(8, 18, 32, 0.92), rgba(8, 18, 32, 0.68));
                border: 1px solid var(--line);
                border-radius: 24px;
                padding: 1.2rem 1.2rem 0.8rem;
                backdrop-filter: blur(14px);
                box-shadow: 0 24px 80px rgba(2, 6, 23, 0.35);
                margin-bottom: 1rem;
            }

            .workspace-kicker {
                color: var(--accent);
                font-size: 0.8rem;
                letter-spacing: 0.12em;
                text-transform: uppercase;
                font-weight: 700;
            }

            .workspace-title {
                color: white;
                font-size: 2.1rem;
                font-weight: 700;
                margin: 0.15rem 0 0.35rem;
            }

            .workspace-copy {
                color: var(--muted);
                margin: 0;
            }

            .panel-card {
                background: var(--panel);
                border: 1px solid var(--line);
                border-radius: 20px;
                padding: 1rem 1.1rem;
                margin-bottom: 0.8rem;
                backdrop-filter: blur(10px);
            }

            .panel-card strong {
                color: white;
            }

            .signal-pill {
                display: inline-flex;
                align-items: center;
                gap: 0.4rem;
                padding: 0.35rem 0.7rem;
                border-radius: 999px;
                font-size: 0.85rem;
                font-weight: 700;
                border: 1px solid transparent;
            }

            .signal-buy {
                color: #dcfce7;
                background: rgba(34, 197, 94, 0.14);
                border-color: rgba(34, 197, 94, 0.28);
            }

            .signal-sell {
                color: #ffe4e6;
                background: rgba(251, 113, 133, 0.14);
                border-color: rgba(251, 113, 133, 0.28);
            }

            .signal-hold {
                color: #fef3c7;
                background: rgba(245, 158, 11, 0.14);
                border-color: rgba(245, 158, 11, 0.28);
            }

            .mini-label {
                color: var(--muted);
                font-size: 0.82rem;
                margin-bottom: 0.35rem;
            }

            .mini-value {
                color: white;
                font-size: 1.15rem;
                font-weight: 700;
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

            .stTextInput label, .stSelectbox label, .stNumberInput label {
                color: var(--muted) !important;
                font-weight: 600 !important;
            }

            .stButton > button {
                border-radius: 14px;
                border: 1px solid rgba(56, 189, 248, 0.35);
                background: linear-gradient(135deg, rgba(14, 165, 233, 0.28), rgba(56, 189, 248, 0.12));
                color: white;
                font-weight: 700;
            }

            .stButton > button:hover {
                border-color: rgba(56, 189, 248, 0.7);
                color: white;
            }
            [data-testid="stMetricValue"] {
                font-size: 1.35rem !important;
                white-space: nowrap !important;
                overflow: visible !important;
                text-overflow: unset !important;
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


def current_period_options(interval: str) -> list[str]:
    return PERIOD_OPTIONS_BY_INTERVAL.get(interval, ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"])


def normalize_period(interval: str) -> None:
    period_options = current_period_options(interval)
    if st.session_state.get("period") not in period_options:
        fallback = "2y" if "2y" in period_options else period_options[min(1, len(period_options) - 1)]
        st.session_state.period = fallback


def render_workspace_intro() -> None:
    st.markdown(
        """
        <div class="workspace-shell">
            <div class="workspace-kicker">Trading Workspace</div>
            <div class="workspace-title">專業量化交易研究平台</div>
            <p class="workspace-copy">多維度市場分析 · 智能策略回測 · AI 趨勢情境推演 → 掃描 → 決策</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_top_controls() -> dict[str, Any]:
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
        return "▲ 買進", "signal-buy"
    if signal == -1:
        return "▼ 賣出", "signal-sell"
    return "◆ 觀望", "signal-hold"


def render_kpi_row(result: dict[str, Any]) -> None:
    df = result["df"]
    kpi = result["kpi"]
    latest = df.iloc[-1]
    signal_text, _ = latest_signal_label(latest.get("signal", 0))
    cols = st.columns(5)
    cols[0].metric("Total Return", f"{kpi['total_return']:.2%}")
    cols[1].metric("Sharpe", f"{kpi['sharpe']:.2f}")
    cols[2].metric("Max Drawdown", f"{kpi['max_drawdown']:.2%}")
    cols[3].metric("Close", f"{latest['close']:.2f}")
    cols[4].metric("Signal", signal_text)


def render_market_panel(result: dict[str, Any], chart_type: str) -> None:
    df = result["df"]
    metadata = result["metadata"]
    latest = df.iloc[-1]
    advice = get_investment_advice(df)
    projection = get_ai_projection(df)
    signal_text, signal_class = latest_signal_label(latest.get("signal", 0))

    left, right = st.columns([3.7, 1.3])
    with left:
        title = f"{metadata['symbol']}  |  {metadata['interval']}  |  {metadata['strategy_name']}"
        st.plotly_chart(create_price_chart(df, title=title, chart_type=chart_type), use_container_width=True)
    with right:
        st.markdown(
            f"""
            <div class="panel-card">
                <div class="mini-label">最新訊號</div>
                <div class="signal-pill {signal_class}">{signal_text}</div>
                <div style="height:0.8rem"></div>
                <div class="mini-label">AI 情緒</div>
                <div class="mini-value">{projection['sentiment']}</div>
                <div class="mini-label" style="margin-top:0.7rem">分析時間</div>
                <div>{metadata['generated_at']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="panel-card">
                <div class="mini-label">Decision Notes</div>
                <div><strong>{advice['advice']}</strong></div>
                <div style="color:#94a3b8; margin-top:0.5rem;">{'<br>'.join(advice['reasons'][:3])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="panel-card">
                <div class="mini-label">Risk Radar</div>
                <div class="mini-value">{projection['risk_score']:.1f} / 100</div>
                <div style="color:#94a3b8; margin-top:0.45rem;">{projection['risk_reason']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_analysis_tab(result: dict[str, Any], chart_type: str) -> None:
    render_kpi_row(result)
    st.markdown("### 市場分析圖表")
    render_market_panel(result, chart_type)

    df = result["df"]
    lower_left, lower_right = st.columns([1.45, 1])
    with lower_left:
        if result["metadata"]["strategy_name"] == "RSI_MACD":
            overbought = result["metadata"]["parameters"].get("overbought", 70)
            oversold = result["metadata"]["parameters"].get("oversold", 30)
            st.plotly_chart(create_rsi_chart(df, overbought, oversold), use_container_width=True)
        else:
            st.info("選擇 RSI_MACD 策略以顯示動能指標圖。")
    with lower_right:
        forecast_df = predict_future_prices(df)
        if forecast_df.empty:
            st.info("資料不足，無法產生情境預測圖。")
        else:
            st.plotly_chart(create_forecast_chart(df, forecast_df), use_container_width=True)


def render_backtest_tab(result: dict[str, Any]) -> None:
    df = result["df"]
    st.markdown("### 資產曲線")
    top, bottom = st.columns([1.2, 1])
    with top:
        st.plotly_chart(create_equity_curve(df), use_container_width=True)
    with bottom:
        latest = df.iloc[-1]
        st.markdown(
            """
            <div class="panel-card">
                <div class="mini-label">持倉監控</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2)
        col1.metric("部位", f"{latest.get('position', 0):.0f}")
        col2.metric("當期策略報酬", f"{latest.get('strategy_returns', 0):.2%}")
        if "equity" in df.columns:
            equity_peak = df["equity"].cummax()
            drawdown = (df["equity"] / equity_peak - 1).min()
            st.metric("最大回撤", f"{drawdown:.2%}")

    display_cols = [
        "open",
        "high",
        "low",
        "close",
        "signal",
        "position",
        "strategy_returns",
        "equity",
    ]
    existing_cols = [col for col in display_cols if col in df.columns]
    st.markdown("### 最近交易明細")
    st.dataframe(df[existing_cols].tail(30), use_container_width=True, height=420)


def render_ai_tab(result: dict[str, Any]) -> None:
    df = result["df"]
    projection = get_ai_projection(df)
    scenarios = projection.get("scenarios", {})
    c1, c2, c3 = st.columns(3)
    c1.metric("Trend Score", f"{projection['trend_score']:.0f}")
    c2.metric("Risk Score", f"{projection['risk_score']:.0f}")
    c3.metric("AI Stance", projection["sentiment"])

    left, right = st.columns([1.25, 1])
    with left:
        st.markdown("### AI 分析依據")
        for reason in projection["trend_reasons"]:
            st.write(f"- {reason}")
        st.write(f"- {projection['risk_reason']}")
    with right:
        st.markdown("### 未來 10 日情境")
        if scenarios:
            st.write(f"- 🟢 樂觀：{scenarios['bullish']:.2f}")
            st.write(f"- ⚪ 中性：{scenarios['neutral_lower']:.2f} ~ {scenarios['neutral_upper']:.2f}")
            st.write(f"- 🔴 悲觀：{scenarios['bearish']:.2f}")
        else:
            st.info("資料不足，無法計算情境。")


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
    st.caption("輸入多個標的代碼（逗號分隔），系統將執行多維度分析並輸出分數排名。")

    default_symbols = "2330.TW, 2317.TW, 2454.TW, 2382.TW, 2881.TW"
    symbol_text = st.text_area("掃描清單", value=default_symbols, height=100)
    scan_period = st.selectbox("掃描區間", ["1mo", "3mo", "6mo", "1y"], index=1, key="scanner_period")
    if st.button("開始掃描", use_container_width=True):
        symbols = [item.strip() for item in symbol_text.split(",") if item.strip()]
        if not symbols:
            st.warning("請輸入至少一個標的代碼。")
        else:
            with st.spinner("掃描中..."):
                result_df = run_screener(symbols, strategy_name, params, tc, scan_period, interval)
            st.success(f"掃描完成！共分析 {len(result_df)} 個標的。")

    watchlist = get_watchlist()
    if watchlist:
        st.markdown("### 最愛清單掃描")
        if st.button("掃描最愛清單", use_container_width=True):
            with st.spinner("分析 watchlist 中..."):
                result_df = run_screener(watchlist, strategy_name, params, tc, "3mo", interval)
            st.success(f"Watchlist 掃描完成！共分析 {len(result_df)} 個標的。")


def render_sidebar(symbol: str, strategy_name: str, interval: str) -> None:
    with st.sidebar:
        st.markdown("## Workspace Sidecar")
        st.caption("管理最愛 watchlist，快速切換標的或一鍵產出報告。")

        watchlist = get_watchlist()
        st.markdown("### Watchlist")
        if symbol:
            if symbol in watchlist:
                if st.button(f"❌ 移除 {symbol}", use_container_width=True):
                    remove_from_watchlist(symbol)
                    st.rerun()
            else:
                if st.button(f"⭐ 加入 {symbol}", use_container_width=True):
                    save_to_watchlist(symbol)
                    st.rerun()

        if watchlist:
            for item in watchlist:
                if st.button(item, key=f"watch_{item}", use_container_width=True):
                    st.session_state.symbol_input = item
                    st.rerun()
        else:
            st.info("清單為空，請加入標的。")

        st.markdown("### Daily Report")
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
        if history.empty:
            st.caption("尚無分析紀錄。")
        else:
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
    render_workspace_intro()

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

    tab1, tab2, tab3, tab4 = st.tabs(["分析", "回測", "Scanner", "AI"])
    latest_result = st.session_state.get("latest_result")
    chart_type = st.session_state.get("last_chart_type", control_state["chart_type"])

    with tab1:
        if latest_result:
            render_analysis_tab(latest_result, chart_type)
        else:
            st.info("請點擊上方 Run 按鈕開始分析，結果將顯示於此頁。")

    with tab2:
        if latest_result:
            render_backtest_tab(latest_result)
        else:
            st.info("請先執行分析，回測績效將顯示於此頁。")

    with tab3:
        render_scanner_tab(
            control_state["strategy_name"],
            strategy_params,
            transaction_cost,
            control_state["interval"],
        )

    with tab4:
        if latest_result:
            render_ai_tab(latest_result)
        else:
            st.info("請先執行分析，AI 情境推演結果將顯示於此頁。")


if __name__ == "__main__":
    main()
