import json
import os
import datetime
import pandas as pd

STORAGE_DIR = "configs/user_data"
WATCHLIST_FILE = os.path.join(STORAGE_DIR, "watchlist.json")
HISTORY_FILE = os.path.join(STORAGE_DIR, "history.csv")

def ensure_storage():
    os.makedirs(STORAGE_DIR, exist_ok=True)
    if not os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "w") as f:
            json.dump([], f)
    if not os.path.exists(HISTORY_FILE):
        df = pd.DataFrame(columns=["timestamp", "symbol", "interval", "score", "sentiment"])
        df.to_csv(HISTORY_FILE, index=False)

def get_watchlist():
    ensure_storage()
    with open(WATCHLIST_FILE, "r") as f:
        return json.load(f)

def save_to_watchlist(symbol: str):
    ensure_storage()
    watchlist = get_watchlist()
    if symbol not in watchlist:
        watchlist.append(symbol)
        with open(WATCHLIST_FILE, "w") as f:
            json.dump(watchlist, f)
        return True
    return False

def remove_from_watchlist(symbol: str):
    ensure_storage()
    watchlist = get_watchlist()
    if symbol in watchlist:
        watchlist.remove(symbol)
        with open(WATCHLIST_FILE, "w") as f:
            json.dump(watchlist, f)
        return True
    return False

def log_access(symbol: str, interval: str, score: int, sentiment: str):
    ensure_storage()
    new_entry = pd.DataFrame([{
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "symbol": symbol,
        "interval": interval,
        "score": score,
        "sentiment": sentiment
    }])
    new_entry.to_csv(HISTORY_FILE, mode='a', header=False, index=False)

def get_history(limit=20):
    ensure_storage()
    try:
        df = pd.read_csv(HISTORY_FILE)
        return df.tail(limit).iloc[::-1]
    except:
        return pd.DataFrame()
