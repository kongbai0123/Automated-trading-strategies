import datetime

import pandas as pd
import requests


def fetch_tw_institutional_data(date_str: str) -> pd.DataFrame:
    """
    Fetch Three Major Institutional Investors data from TWSE for a specific date.
    date_str: YYYYMMDD
    """
    url = f"https://www.twse.com.tw/rwd/zh/fund/T86?response=json&date={date_str}&selectType=ALL"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get("stat") != "OK":
            return pd.DataFrame()

        cols = data["fields"]
        rows = data["data"]
        df = pd.DataFrame(rows, columns=cols)
        # Clean column names (remove spaces/newlines)
        df.columns = [c.replace(" ", "").replace("\n", "") for c in df.columns]
        return df
    except Exception as e:
        print(f"Error fetching institutional data: {e}")
        return pd.DataFrame()


_DAILY_CHIPS_CACHE = {}


def get_daily_chips_table(date_str: str) -> pd.DataFrame:
    global _DAILY_CHIPS_CACHE
    if date_str in _DAILY_CHIPS_CACHE:
        return _DAILY_CHIPS_CACHE[date_str]

    df = fetch_tw_institutional_data(date_str)
    if not df.empty:
        _DAILY_CHIPS_CACHE[date_str] = df
    return df


def get_latest_chips(symbol: str) -> dict:
    """
    Get the latest institutional buy/sell for a specific symbol using a cached table.
    """
    target_date = datetime.datetime.now()
    clean_sym = symbol.split(".")[0]

    for _ in range(5):
        date_str = target_date.strftime("%Y%m%d")
        df = get_daily_chips_table(date_str)
        if not df.empty:
            row = df[df["證券代號"] == clean_sym]
            if not row.empty:
                r = row.iloc[0]
                return {
                    "date": date_str,
                    "foreign": r.get("外資買賣超股數", "0"),
                    "trust": r.get("投信買賣超股數", "0"),
                    "dealer": r.get("自營商買賣超股數", "0"),
                    "total": r.get("三大法人買賣超股數", "0"),
                }
        target_date -= datetime.timedelta(days=1)

    return {"foreign": "0", "trust": "0", "dealer": "0", "total": "0", "date": "未知"}


def parse_val(val: str) -> float:
    try:
        return float(val.replace(",", ""))
    except (AttributeError, ValueError):
        return 0.0


def get_chip_score(chips: dict) -> tuple:
    """
    Calculate a chip score and reason.
    """
    f = parse_val(chips.get("foreign", "0"))
    t = parse_val(chips.get("trust", "0"))
    score = 0
    reasons = []

    if f > 0:
        score += 15
        reasons.append("外資買進")
    elif f < 0:
        score -= 10
        reasons.append("外資賣出")

    if t > 0:
        score += 20
        reasons.append("投信加碼")
    elif t < 0:
        score -= 15
        reasons.append("投信調節")

    return score, ", ".join(reasons) if reasons else "無明顯變動"
