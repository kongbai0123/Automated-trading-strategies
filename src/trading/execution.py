from datetime import datetime, timedelta


class NextBarExecutionPolicy:
    def next_market_time(self, market_time: datetime, timeframe: str) -> datetime:
        if timeframe == "1d":
            return market_time + timedelta(days=1)
        raise NotImplementedError(f"Unsupported timeframe: {timeframe}")
