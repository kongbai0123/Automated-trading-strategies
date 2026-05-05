import streamlit as st
import os
import glob
import sys
import pandas as pd
import json

# Ensure we can import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.ui_pipeline import run_backtest_pipeline, load_config
from src.strategy_registry import StrategyRegistry
from src.charting import create_price_chart, create_equity_curve, create_rsi_chart, create_forecast_chart
from src.predictor import predict_future_prices, get_investment_advice
from src.assets_icons import ICONS
from src.storage import get_watchlist, save_to_watchlist, remove_from_watchlist, log_access, get_history
from src.automation import generate_daily_report

st.set_page_config(page_title="量化交易分析系統", layout="wide")

# --- 注入自定義 CSS 實現高品質提示效果與現代化設計 ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --primary: #3b82f6;
        --up: #10b981;
        --down: #f43f5e;
        --bg-dark: #0f172a;
        --card-bg: rgba(30, 41, 59, 0.7);
        --border-color: rgba(255, 255, 255, 0.1);
    }

    /* 全局樣式優化 */
    .stApp {
        background: radial-gradient(circle at top right, #1e293b, #0f172a);
        font-family: 'Inter', sans-serif;
    }

    /* 玻璃擬態卡片 */
    .glass-card {
        background: var(--card-bg);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        transition: transform 0.3s ease, border-color 0.3s ease;
    }

    .glass-card:hover {
        transform: translateY(-5px);
        border-color: rgba(255, 255, 255, 0.2);
    }

    /* KPI 卡片內容 */
    .kpi-container {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }

    .kpi-header {
        display: flex;
        align-items: center;
        gap: 10px;
        color: rgba(255, 255, 255, 0.6);
        font-size: 0.9rem;
        font-weight: 500;
    }

    .kpi-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: white;
        margin: 5px 0;
    }

    .kpi-delta {
        font-size: 0.85rem;
        display: flex;
        align-items: center;
        gap: 4px;
    }

    .kpi-delta.up { color: var(--up); }
    .kpi-delta.down { color: var(--down); }

    /* 提示符號容器 */
    .custom-tooltip {
        position: relative;
        display: inline-block;
        margin-left: 8px;
        cursor: help;
        font-weight: bold;
        color: var(--primary);
        opacity: 0.6;
        transition: opacity 0.3s ease;
    }
    
    .custom-tooltip:hover {
        opacity: 1.0;
    }
    
    .custom-tooltip .tooltiptext {
        visibility: hidden;
        width: 280px;
        background-color: #1e293b;
        color: #ffffff;
        text-align: left;
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 15px;
        position: absolute;
        z-index: 9999;
        bottom: 130%;
        left: 50%;
        margin-left: -140px;
        opacity: 0;
        transition: opacity 0.3s;
        box-shadow: 0px 10px 25px rgba(0,0,0,0.5);
    }
    
    .custom-tooltip:hover .tooltiptext {
        visibility: visible;
        opacity: 1;
    }
    
    /* 側邊欄與標題優化 */
    .label-container {
        display: flex;
        align-items: center;
        margin-bottom: 8px;
    }

    h1, h2, h3 {
        color: white !important;
        font-weight: 700 !important;
    }

    .stButton>button {
        border-radius: 8px !important;
        background: var(--primary) !important;
        border: none !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.3s !important;
    }

    .stButton>button:hover {
        opacity: 0.9 !important;
        box-shadow: 0 0 15px rgba(59, 130, 246, 0.4) !important;
    }
</style>
""", unsafe_allow_html=True)

# Load Configuration
config = load_config()
data_dir = config.get("data_dir", "data")
default_tc = config.get("transaction_cost", 0.001)
strategy_defaults = config.get("strategy_defaults", {})

# 策略說明內容
STRATEGY_HINT = {
    "RSI_MACD": """<b>RSI + MACD 綜合策略</b><br><br>結合超買超賣與趨勢動能。當 RSI < 30 且 MACD 翻正時買入；當 RSI > 70 且 MACD 翻負時賣出。適合捕捉市場轉折點。""",
    "MA_CROSSOVER": """<b>移動平均交叉策略 (MA)</b><br><br>經典趨勢追隨策略。短期均線向上突破長期均線時買入(黃金交叉)；跌破時賣出(死亡交叉)。適合波段趨勢行情。"""
}

def sidebar_controls():
    st.sidebar.header("⚙️ 系統設定")
    
    # 1. On-Demand Fetching inputs
    symbol = st.sidebar.text_input("輸入標的代碼 (例: 2330.TW, AAPL)", "2330.TW")
    
    # Timeframe selection
    timeframe_options = {
        "月 K": "1mo",
        "週 K": "1wk",
        "日 K": "1d",
        "60 分鐘": "60m",
        "15 分鐘": "15m",
        "5 分鐘": "5m",
        "1 分鐘": "1m"
    }
    selected_tf_label = st.sidebar.selectbox("分析週期 (Timeframe)", list(timeframe_options.keys()), index=2)
    interval = timeframe_options[selected_tf_label]
    
    # Period selection with dynamic defaults based on interval
    if interval in ["1m", "5m"]:
        period_options = ["1d", "5d", "7d"]
        period_idx = 1
    elif interval in ["15m", "60m"]:
        period_options = ["1d", "5d", "1mo", "3mo"]
        period_idx = 2
    else:
        period_options = ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"]
        period_idx = 4
        
    period = st.sidebar.selectbox("分析區間 (Period)", period_options, index=period_idx)
    chart_type = st.sidebar.selectbox("圖表類型", ["Candlestick", "Line", "OHLC"])
    
    st.sidebar.divider()
    
    # --- 實現您的自定義 ! 提示符號 ---
    strategies = StrategyRegistry.get_available_strategies()
    
    hint_html = f"""
    <div class="label-container">
        <span style="font-weight: 500;">📈 選擇交易策略</span>
        <div class="custom-tooltip">!
            <span class="tooltiptext">
                <b>💡 策略小提示</b><br><br>
                - <b>RSI_MACD</b>: 逆勢反轉策略<br>
                - <b>MA_CROSSOVER</b>: 順勢波段策略<br>
                - <b>BOLLINGER_BREAKOUT</b>: 突破策略
            </span>
        </div>
    </div>
    """
    st.sidebar.markdown(hint_html, unsafe_allow_html=True)
    
    selected_strategy = st.sidebar.selectbox(
        "📈 選擇交易策略", 
        strategies, 
        label_visibility="collapsed"
    )
    
    # Strategy Parameters
    st.sidebar.subheader("🛠️ 策略參數調整")
    strategy_params = {}
    if selected_strategy == "RSI_MACD":
        defaults = strategy_defaults.get("RSIMACDStrategy", {"overbought": 70, "oversold": 30})
        strategy_params["overbought"] = st.sidebar.slider("RSI 超買門檻", 50, 100, defaults["overbought"])
        strategy_params["oversold"] = st.sidebar.slider("RSI 超賣門檻", 0, 50, defaults["oversold"])
    elif selected_strategy == "MA_CROSSOVER":
        defaults = strategy_defaults.get("MACrossoverStrategy", {"short_col": "sma_20", "long_col": "sma_50"})
        strategy_params["short_col"] = st.sidebar.text_input("短期均線名稱", defaults["short_col"])
        strategy_params["long_col"] = st.sidebar.text_input("長期均線名稱", defaults["long_col"])
    elif selected_strategy == "BOLLINGER_BREAKOUT":
        defaults = strategy_defaults.get("BollingerBreakoutStrategy", {"close_col": "close", "upper_col": "bb_upper", "lower_col": "bb_lower"})
        strategy_params["upper_col"] = st.sidebar.text_input("上軌名稱", defaults["upper_col"])
        strategy_params["lower_col"] = st.sidebar.text_input("下軌名稱", defaults["lower_col"])
        
    st.sidebar.divider()
    
    # Watchlist Management
    st.sidebar.subheader("⭐ 我的最愛標的")
    watchlist = get_watchlist()
    if symbol in watchlist:
        if st.sidebar.button(f"❌ 從最愛移除 {symbol}", use_container_width=True):
            remove_from_watchlist(symbol)
            st.rerun()
    else:
        if st.sidebar.button(f"⭐ 加入最愛 {symbol}", use_container_width=True):
            save_to_watchlist(symbol)
            st.rerun()
            
    if watchlist:
        st.sidebar.caption("快速選擇：")
        cols = st.sidebar.columns(2)
        for i, s in enumerate(watchlist):
            if cols[i % 2].button(s, key=f"wl_{s}", use_container_width=True):
                # This is tricky in Streamlit, usually needs a query param or session state
                st.session_state['force_symbol'] = s
                st.rerun()

    st.sidebar.divider()
    transaction_cost = st.sidebar.number_input("手續費率 (TC)", min_value=0.0, max_value=0.1, value=default_tc, step=0.0001, format="%.4f")
    
    # Automation Button
    if st.sidebar.button("📄 產生每日掃描報告", use_container_width=True):
        with st.spinner("產生報告中..."):
            report_path = generate_daily_report(watchlist if watchlist else [symbol], selected_strategy, interval)
            if report_path:
                st.sidebar.success(f"報告已產出：{report_path}")
            else:
                st.sidebar.error("報告產出失敗。")

    run_btn = st.sidebar.button("🚀 開始分析與回測", type="primary", use_container_width=True)
    
    return symbol, period, interval, chart_type, selected_strategy, strategy_params, transaction_cost, run_btn

def render_custom_kpi_cards(kpi: dict):
    st.markdown("### 📊 策略績效總結")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        color_class = "up" if kpi['total_return'] >= 0 else "down"
        icon = ICONS["trending-up"] if kpi['total_return'] >= 0 else ICONS["trending-down"]
        st.markdown(f"""
        <div class="glass-card">
            <div class="kpi-container">
                <div class="kpi-header">{ICONS['activity']} 累積報酬率</div>
                <div class="kpi-value">{kpi['total_return']*100:.2f}%</div>
                <div class="kpi-delta {color_class}">{icon} 相對於初始資金</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="glass-card">
            <div class="kpi-container">
                <div class="kpi-header">{ICONS['zap']} 夏普比率</div>
                <div class="kpi-value">{kpi['sharpe']:.2f}</div>
                <div class="kpi-delta" style="color: rgba(255,255,255,0.4)">風險調整後收益</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="glass-card">
            <div class="kpi-container">
                <div class="kpi-header">{ICONS['trending-down']} 最大回撤 (MDD)</div>
                <div class="kpi-value" style="color: var(--down)">{kpi['max_drawdown']*100:.2f}%</div>
                <div class="kpi-delta down">歷史最大資產回落</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_advice_section(advice: dict):
    st.divider()
    st.markdown(f"### {ICONS['target']} 系統智慧評估")
    
    bg_color = "rgba(16, 185, 129, 0.1)" if advice['color'] == "green" else "rgba(244, 63, 94, 0.1)"
    border_color = "#10b981" if advice['color'] == "green" else "#f43f5e"
    if advice['color'] == "gray": 
        bg_color = "rgba(148, 163, 184, 0.1)"
        border_color = "#94a3b8"
        
    st.markdown(f"""
    <div style="padding: 24px; border-radius: 16px; background-color: {bg_color}; border: 1px solid {border_color}; backdrop-filter: blur(8px);">
        <h2 style="color: {border_color}; margin-top: 0; display: flex; align-items: center; gap: 12px;">
            {advice['advice']}
        </h2>
        <div style="color: rgba(255,255,255,0.8); font-size: 1.1rem; margin-top: 15px;">
            <ul style="margin-bottom: 0;">{"".join([f"<li style='margin-bottom: 8px;'>{r}</li>" for r in advice['reasons']])}</ul>
        </div>
    </div>
    """, unsafe_allow_html=True)

from src.predictor import get_investment_advice, predict_future_prices, get_ai_projection

def render_ai_projection(df: pd.DataFrame):
    projection = get_ai_projection(df)
    st.divider()
    st.markdown(f"### {ICONS['zap']} AI 趨勢情境推演 (Beta)")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("**趨勢評分 (Trend Score)**")
        st.progress(projection['trend_score'] / 100)
        st.markdown(f"目前態度：<span style='color:{projection['color']}; font-weight:bold; font-size:1.2rem;'>{projection['sentiment']}</span>", unsafe_allow_html=True)
        st.write("**關鍵依據：**")
        for r in projection['trend_reasons']:
            st.markdown(f"- {r}")
            
    with col2:
        st.write("**風險評分 (Risk Score)**")
        st.progress(projection['risk_score'] / 100)
        st.write(f"**風險診斷：** {projection['risk_reason']}")
        
        st.write("**未來 10 日情境預估：**")
        sc = projection['scenarios']
        if sc:
            st.markdown(f"""
            - 🟢 **樂觀情境**：{sc['bullish']:.2f} (上方邊界)
            - ⚪ **中性區間**：{sc['neutral_lower']:.2f} ~ {sc['neutral_upper']:.2f}
            - 🔴 **悲觀情境**：{sc['bearish']:.2f} (下方邊界)
            """)

def render_main(result: dict, chart_type: str):
    interval_display = result['metadata'].get('interval', '1d')
    st.markdown(f"## 🔍 正在分析：{result['metadata']['symbol']} ({interval_display})")
    render_custom_kpi_cards(result['kpi'])
    
    df = result['df']
    render_ai_projection(df)
    
    advice = get_investment_advice(df)
    render_advice_section(advice)
    st.divider()
    st.subheader("📈 價格走勢與交易標記")
    df = result['df']
    st.plotly_chart(create_price_chart(df, chart_type=chart_type), use_container_width=True)
    st.subheader("🔮 未來預測與資產變化")
    col_a, col_b = st.columns(2)
    with col_a:
        forecast_df = predict_future_prices(df)
        if not forecast_df.empty: st.plotly_chart(create_forecast_chart(df, forecast_df), use_container_width=True)
        else: st.info("暫無足夠資料進行預測。")
    with col_b: st.plotly_chart(create_equity_curve(df), use_container_width=True)
    if result['metadata']['strategy_name'] == "RSI_MACD":
        ob = result['metadata']['parameters'].get('overbought', 70)
        osold = result['metadata']['parameters'].get('oversold', 30)
        st.plotly_chart(create_rsi_chart(df, ob, osold), use_container_width=True)
    st.divider()
    st.subheader("📝 最新交易明細 (最近 20 筆)")
    display_cols = ['open', 'high', 'low', 'close', 'signal', 'position', 'strategy_returns', 'equity']
    existing_cols = [c for c in display_cols if c in df.columns]
    st.dataframe(df[existing_cols].tail(20), use_container_width=True)

from src.scanner import analyze_symbol_detailed

def run_screener(symbols: list, strategy_name: str, params: dict, tc: float, period: str, interval: str = "1d"):
    results = []
    progress_bar = st.progress(0)
    
    # Create a placeholder for the live table
    table_placeholder = st.empty()
    
    for i, sym in enumerate(symbols):
        try:
            res = run_backtest_pipeline(sym, strategy_name, params, tc, period, interval)
            df = res['df']
            analysis = analyze_symbol_detailed(df, symbol=sym)
            latest = df.iloc[-1]
            
            signal_text = "🟢 買進" if latest['signal'] == 1 else "🔴 賣出" if latest['signal'] == -1 else "⚪ 觀望"
            
            results.append({
                "標的": sym,
                "分數": analysis['score'],
                "趨勢": analysis['trend'],
                "訊號": signal_text,
                "風險": analysis['risk'],
                "量能比": f"{analysis['volume_ratio']:.1f}x",
                "累積報酬": f"{res['kpi']['total_return']*100:.2f}%",
                "分析依據": analysis['reason']
            })
        except Exception as e:
            results.append({"標的": sym, "分數": 0, "趨勢": "⚠️ 錯誤", "訊號": "-", "風險": "-", "量能比": "-", "累積報酬": "-", "分析依據": str(e)})
        
        progress_bar.progress((i + 1) / len(symbols))
        # Update table live
        current_df = pd.DataFrame(results)
        table_placeholder.dataframe(current_df, use_container_width=True)
    
    st.success(f"✅ 掃描完成！共分析 {len(symbols)} 個標的。")

def main():
    st.title("💡 專業量化交易分析系統")
    
    # Handle force symbol from watchlist click
    default_sym = st.session_state.get('force_symbol', "2330.TW")
    # We need to manually clear it after use or it sticks
    if 'force_symbol' in st.session_state:
        del st.session_state['force_symbol']
        
    # Sidebar needs to know the default sym if we clicked one
    # Note: sidebar_controls might need adjustment to take a default, but for now we rely on the widget ID or state
    symbol, period, interval, chart_type, strategy_name, params, tc, run_btn = sidebar_controls()
    
    tab1, tab2, tab3, tab4 = st.tabs(["🔍 單一商品分析", "📊 多商品掃描器", "⭐ 最愛標度掃描", "📜 分析紀錄"])
    
    with tab1:
        if run_btn:
            if not symbol:
                st.error("無法執行：請輸入股票代碼。")
                return
            with st.spinner(f"系統正在連線抓取 {symbol} 資料並分析中..."):
                try:
                    result = run_backtest_pipeline(symbol, strategy_name, params, tc, period, interval)
                    st.session_state['latest_result'] = result
                    st.session_state['last_chart_type'] = chart_type
                    # Log Access
                    from src.predictor import get_ai_projection
                    proj = get_ai_projection(result['df'])
                    log_access(symbol, interval, proj['trend_score'], proj['sentiment'])
                except Exception as e:
                    st.error(f"運算錯誤: {str(e)}")
                    return
        
        if 'latest_result' in st.session_state:
            render_main(st.session_state['latest_result'], st.session_state.get('last_chart_type', 'Candlestick'))
        else:
            st.info("⬅️ 請在左側設定參數，並點擊「開始分析與回測」。")
            
    with tab2:
        st.header("多商品即時掃描")
        st.write("掃描自定義清單中的標的。")
        default_symbols = "2330.TW, 2317.TW, 2454.TW, 2382.TW, 2881.TW"
        screener_input = st.text_input("輸入掃描清單 (逗號分隔)", default_symbols)
        if st.button("開始全域掃描"):
            symbols_list = [s.strip() for s in screener_input.split(",") if s.strip()]
            with st.spinner("掃描中..."):
                run_screener(symbols_list, strategy_name, params, tc, "3mo", interval)

    with tab3:
        st.header("⭐ 我的最愛即時掃描")
        watchlist = get_watchlist()
        if not watchlist:
            st.warning("目前最愛清單為空。請先在左側將標的加入最愛。")
        else:
            st.write(f"目前追蹤：{', '.join(watchlist)}")
            if st.button("執行最愛清單分析"):
                with st.spinner("分析中最愛標的..."):
                    run_screener(watchlist, strategy_name, params, tc, period, interval)

    with tab4:
        st.header("📜 最近分析紀錄")
        history = get_history(30)
        if not history.empty:
            st.dataframe(history, use_container_width=True)
            if st.button("清除紀錄"):
                ensure_storage()
                pd.DataFrame(columns=["timestamp", "symbol", "interval", "score", "sentiment"]).to_csv(HISTORY_FILE, index=False)
                st.rerun()
        else:
            st.info("尚無分析紀錄。")

if __name__ == "__main__":
    from src.storage import ensure_storage, HISTORY_FILE # Import for clear action
    ensure_storage()
    main()
