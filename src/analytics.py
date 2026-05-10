import numpy as np
import pandas as pd


def calculate_kpi(df: pd.DataFrame) -> dict:
    """
    計算回測績效指標。

    必要欄位：equity, strategy_returns
    選用欄位：position（用於勝率 / 盈虧比 / 交易次數 / 持倉比例）

    所有除以零的情況皆回傳 0（安全值），不拋出例外。
    """
    if "equity" not in df.columns or "strategy_returns" not in df.columns:
        raise ValueError("DataFrame must contain 'equity' and 'strategy_returns' columns")

    equity = df["equity"]
    returns = df["strategy_returns"].dropna()

    # ── 基礎三指標 ────────────────────────────────────────────────
    total_return: float = float(equity.iloc[-1] - 1)

    sharpe: float = (
        float(np.sqrt(252) * returns.mean() / returns.std()) if returns.std() != 0 else 0.0
    )

    drawdown = equity / equity.cummax() - 1
    mdd: float = float(drawdown.min())

    # ── Calmar Ratio（年化報酬 / |MDD|）─────────────────────────
    n_years = len(df) / 252
    annualized_return = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else 0.0
    calmar: float = float(annualized_return / abs(mdd)) if mdd != 0 else 0.0

    # ── 交易化指標（需要 position 欄位）─────────────────────────
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    exposure: float = 0.0

    if "position" in df.columns:
        pos = df["position"]

        # 持倉比例：非零部位佔全部 bars 的比例
        exposure = float((pos != 0).mean())

        # 換手次數：position 改變視為一次交易（buy or sell）
        trades_series = pos.diff().abs()
        total_trades = int(trades_series[trades_series > 0].count())

        # 以「每次持倉區段的累積策略報酬」計算每筆交易損益
        if "strategy_returns" in df.columns and total_trades > 0:
            sr = df["strategy_returns"].fillna(0)
            trade_id = (pos.diff().abs() > 0).cumsum()
            active = pos != 0
            trade_pnl = sr[active].groupby(trade_id[active]).sum()
            winning = trade_pnl[trade_pnl > 0]
            losing = trade_pnl[trade_pnl < 0]

            n_trades = len(trade_pnl)
            win_rate = float(len(winning) / n_trades) if n_trades > 0 else 0.0

            total_profit = float(winning.sum())
            total_loss = float(abs(losing.sum()))
            profit_factor = float(total_profit / total_loss) if total_loss != 0 else 0.0

    return {
        "total_return": total_return,
        "sharpe": sharpe,
        "max_drawdown": mdd,
        "calmar_ratio": calmar,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "total_trades": total_trades,
        "exposure": exposure,
    }
