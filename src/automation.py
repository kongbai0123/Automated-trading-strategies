import os
import pandas as pd
import datetime
from .ui_pipeline import run_backtest_pipeline
from .scanner import analyze_symbol_detailed

def generate_daily_report(symbols: list, strategy_name: str, interval: str = "1d"):
    """
    執行批次分析並產生 HTML 報告。
    """
    report_dir = "reports"
    os.makedirs(report_dir, exist_ok=True)
    
    today = datetime.datetime.now().strftime("%Y%m%d")
    report_path = os.path.join(report_dir, f"market_report_{today}.html")
    
    results = []
    for sym in symbols:
        try:
            res = run_backtest_pipeline(sym, strategy_name, {}, 0.001, "1y", interval)
            analysis = analyze_symbol_detailed(res['df'], symbol=sym)
            results.append({
                "Symbol": sym,
                "Score": analysis['score'],
                "Trend": analysis['trend'],
                "Risk": analysis['risk'],
                "Reason": analysis['reason'],
                "Return": f"{res['kpi']['total_return']*100:.2f}%"
            })
        except:
            continue
            
    df = pd.DataFrame(results)
    if df.empty:
        return None
        
    # Sort by score
    df = df.sort_values(by="Score", ascending=False)
    
    html_content = f"""
    <html>
    <head>
        <title>每日市場掃描報告 - {today}</title>
        <style>
            body {{ font-family: sans-serif; background-color: #0f172a; color: white; padding: 20px; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
            th, td {{ border: 1px solid #334155; padding: 12px; text-align: left; }}
            th {{ background-color: #1e293b; color: #3b82f6; }}
            tr:nth-child(even) {{ background-color: #1e293b; }}
            .high-score {{ color: #10b981; font-weight: bold; }}
            .low-score {{ color: #f43f5e; }}
        </style>
    </head>
    <body>
        <h1>📈 每日市場掃描報告 ({today})</h1>
        <p>分析策略：{strategy_name} | 週期：{interval}</p>
        {df.to_html(index=False, classes='table')}
    </body>
    </html>
    """
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    return report_path
