import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# 現代化配色方案
COLOR_UP = '#10b981'     # Emerald 500
COLOR_DOWN = '#f43f5e'   # Rose 500
COLOR_PRIMARY = '#3b82f6' # Blue 500
COLOR_GRID = 'rgba(255, 255, 255, 0.05)'
COLOR_TEXT = 'rgba(255, 255, 255, 0.7)'

def create_price_chart(df: pd.DataFrame, title: str = "價格走勢圖", chart_type: str = "Candlestick") -> go.Figure:
    """建立包含價格走勢、均線與買賣訊號的圖表。支援 Candlestick, Line, OHLC。"""
    fig = go.Figure()
    
    # K 線圖 / 折線圖 / OHLC
    if chart_type == "Line":
        fig.add_trace(go.Scatter(x=df.index, y=df['close'], mode='lines', name='收盤價', line=dict(color='white', width=2)))
    elif chart_type == "OHLC":
        fig.add_trace(go.Ohlc(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], 
                             increasing_line_color=COLOR_UP, decreasing_line_color=COLOR_DOWN, name="股價"))
    else:
        # Default to Candlestick
        fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], 
                                   increasing_line_color=COLOR_UP, decreasing_line_color=COLOR_DOWN, name="股價"))

    # 均線
    if 'sma_20' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['sma_20'], mode='lines', name='20日均線', line=dict(color='#fbbf24', width=1.5, dash='solid')))
    if 'sma_50' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['sma_50'], mode='lines', name='50日均線', line=dict(color='#8b5cf6', width=1.5, dash='solid')))

    # 買賣標記
    if 'signal' in df.columns:
        buy_signals = df[df['signal'] == 1]
        sell_signals = df[df['signal'] == -1]
        
        fig.add_trace(go.Scatter(
            x=buy_signals.index, y=buy_signals['close'] * 0.97,
            mode='markers', name='買入訊號',
            marker=dict(symbol='triangle-up', size=14, color=COLOR_UP, line=dict(width=1, color='white'))
        ))
        fig.add_trace(go.Scatter(
            x=sell_signals.index, y=sell_signals['close'] * 1.03,
            mode='markers', name='賣出訊號',
            marker=dict(symbol='triangle-down', size=14, color=COLOR_DOWN, line=dict(width=1, color='white'))
        ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=20, color='white')),
        xaxis_title="日期", yaxis_title="價格",
        template="plotly_dark",
        height=600,
        margin=dict(l=50, r=50, t=80, b=50),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(gridcolor=COLOR_GRID, showgrid=True),
        yaxis=dict(gridcolor=COLOR_GRID, showgrid=True),
        legend=dict(bgcolor='rgba(0,0,0,0.5)', bordercolor='rgba(255,255,255,0.1)', borderwidth=1)
    )
    fig.update_xaxes(rangeslider_visible=False)
    return fig

def create_equity_curve(df: pd.DataFrame) -> go.Figure:
    """建立資產淨值曲線圖。"""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=df['equity'],
        mode='lines', name='資產淨值',
        line=dict(color=COLOR_PRIMARY, width=3),
        fill='tozeroy', fillcolor='rgba(59, 130, 246, 0.1)'
    ))
    fig.update_layout(
        title=dict(text="資產淨值曲線 (Equity Curve)", font=dict(size=18, color='white')),
        xaxis_title="日期", yaxis_title="資產規模",
        template="plotly_dark",
        height=400,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(gridcolor=COLOR_GRID),
        yaxis=dict(gridcolor=COLOR_GRID)
    )
    return fig

def create_forecast_chart(df: pd.DataFrame, forecast_df: pd.DataFrame) -> go.Figure:
    """建立未來價格預測圖。"""
    fig = go.Figure()
    
    # 歷史價格 (最後 30 天)
    hist_subset = df.tail(30)
    fig.add_trace(go.Scatter(x=hist_subset.index, y=hist_subset['close'], mode='lines+markers', name='歷史收盤價', line=dict(color='white', width=2)))
    
    if not forecast_df.empty:
        # 預測價格
        fig.add_trace(go.Scatter(x=forecast_df['date'], y=forecast_df['predicted_price'], mode='lines+markers', name='預測價格', line=dict(color='#fbbf24', width=2, dash='dash')))
        
        # 信心區間
        fig.add_trace(go.Scatter(
            x=pd.concat([forecast_df['date'], forecast_df['date'][::-1]]),
            y=pd.concat([forecast_df['upper_bound'], forecast_df['lower_bound'][::-1]]),
            fill='toself', fillcolor='rgba(251, 191, 36, 0.1)',
            line=dict(color='rgba(251, 191, 36, 0)'),
            hoverinfo="skip", showlegend=True, name="預測區間"
        ))
        
    fig.update_layout(
        title=dict(text="未來 10 交易日價格預測 (Trend Forecast)", font=dict(size=18, color='white')),
        xaxis_title="日期", yaxis_title="價格",
        template="plotly_dark",
        height=400,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(gridcolor=COLOR_GRID),
        yaxis=dict(gridcolor=COLOR_GRID)
    )
    return fig

def create_rsi_chart(df: pd.DataFrame, overbought: int = 70, oversold: int = 30) -> go.Figure:
    """建立 RSI 指標圖。"""
    fig = go.Figure()
    if 'rsi_14' not in df.columns: return fig
        
    fig.add_trace(go.Scatter(x=df.index, y=df['rsi_14'], mode='lines', name='RSI 14', line=dict(color='#ec4899', width=2)))
    fig.add_hline(y=overbought, line_dash="dash", line_color=COLOR_DOWN, annotation_text="超買區", annotation_font_color=COLOR_DOWN)
    fig.add_hline(y=oversold, line_dash="dash", line_color=COLOR_UP, annotation_text="超賣區", annotation_font_color=COLOR_UP)
    
    fig.update_layout(
        title=dict(text="RSI 指標 (14)", font=dict(size=16, color='white')),
        yaxis=dict(range=[0, 100], gridcolor=COLOR_GRID),
        xaxis=dict(gridcolor=COLOR_GRID),
        template="plotly_dark",
        height=300,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    return fig

