import pandas as pd
import numpy as np
from src.utils.config_loader import ConfigLoader


class TechnicalIndicators:
    def __init__(self):
        self.config = ConfigLoader().config

    def calculate_ma(self, df: pd.DataFrame) -> pd.DataFrame:
        ma_config = self.config["indicators"]["ma"]
        df = df.copy()

        df[f"MA_{ma_config['short_period']}"] = df["close"].rolling(window=ma_config["short_period"]).mean()
        df[f"MA_{ma_config['medium_period']}"] = df["close"].rolling(window=ma_config["medium_period"]).mean()
        df[f"MA_{ma_config['long_period']}"] = df["close"].rolling(window=ma_config["long_period"]).mean()

        return df

    def calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        macd_config = self.config["indicators"]["macd"]
        df = df.copy()

        ema_fast = df["close"].ewm(span=macd_config["fast_period"], adjust=False).mean()
        ema_slow = df["close"].ewm(span=macd_config["slow_period"], adjust=False).mean()

        df["MACD"] = ema_fast - ema_slow
        df["MACD_Signal"] = df["MACD"].ewm(span=macd_config["signal_period"], adjust=False).mean()
        df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]

        return df

    def calculate_rsi(self, df: pd.DataFrame) -> pd.DataFrame:
        rsi_config = self.config["indicators"]["rsi"]
        df = df.copy()

        delta = df["close"].diff(1)
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=rsi_config["period"]).mean()
        avg_loss = loss.rolling(window=rsi_config["period"]).mean()

        rs = avg_gain / avg_loss
        df["RSI"] = 100 - (100 / (1 + rs))

        df["RSI_Oversold"] = rsi_config["oversold"]
        df["RSI_Overbought"] = rsi_config["overbought"]

        return df

    def calculate_bollinger_bands(self, df: pd.DataFrame) -> pd.DataFrame:
        bollinger_config = self.config["indicators"]["bollinger"]
        df = df.copy()

        df["BB_Middle"] = df["close"].rolling(window=bollinger_config["period"]).mean()
        df["BB_Std"] = df["close"].rolling(window=bollinger_config["period"]).std()

        df["BB_Upper"] = df["BB_Middle"] + (bollinger_config["num_std"] * df["BB_Std"])
        df["BB_Lower"] = df["BB_Middle"] - (bollinger_config["num_std"] * df["BB_Std"])

        df["BB_Percent"] = (df["close"] - df["BB_Lower"]) / (df["BB_Upper"] - df["BB_Lower"])

        return df

    def calculate_all(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self.calculate_ma(df)
        df = self.calculate_macd(df)
        df = self.calculate_rsi(df)
        df = self.calculate_bollinger_bands(df)
        return df

    def get_latest_indicators(self, df: pd.DataFrame) -> dict:
        if df.empty or len(df) < 10:
            return {}

        last_row = df.iloc[-1]
        prev_row = df.iloc[-2] if len(df) >= 2 else last_row

        ma_config = self.config["indicators"]["ma"]
        rsi_config = self.config["indicators"]["rsi"]

        return {
            "price": {
                "close": last_row["close"],
                "open": last_row["open"],
                "high": last_row["high"],
                "low": last_row["low"],
                "volume": last_row["volume"]
            },
            "ma": {
                f"ma_{ma_config['short_period']}": last_row[f"MA_{ma_config['short_period']}"],
                f"ma_{ma_config['medium_period']}": last_row[f"MA_{ma_config['medium_period']}"],
                f"ma_{ma_config['long_period']}": last_row[f"MA_{ma_config['long_period']}"],
                "trend": self._detect_ma_trend(df)
            },
            "macd": {
                "macd": last_row["MACD"],
                "signal": last_row["MACD_Signal"],
                "hist": last_row["MACD_Hist"],
                "prev_hist": prev_row["MACD_Hist"],
                "crossover": self._detect_macd_crossover(df)
            },
            "rsi": {
                "value": last_row["RSI"],
                "oversold": rsi_config["oversold"],
                "overbought": rsi_config["overbought"],
                "status": self._detect_rsi_status(last_row["RSI"], rsi_config)
            },
            "bollinger": {
                "upper": last_row["BB_Upper"],
                "middle": last_row["BB_Middle"],
                "lower": last_row["BB_Lower"],
                "percent": last_row["BB_Percent"],
                "position": self._detect_bollinger_position(last_row)
            }
        }

    def _detect_ma_trend(self, df: pd.DataFrame) -> str:
        ma_config = self.config["indicators"]["ma"]
        if len(df) < ma_config["long_period"]:
            return "neutral"

        last_row = df.iloc[-1]
        short_ma = last_row[f"MA_{ma_config['short_period']}"]
        medium_ma = last_row[f"MA_{ma_config['medium_period']}"]
        long_ma = last_row[f"MA_{ma_config['long_period']}"]
        close = last_row["close"]

        # 多头排列 + 价格在短期均线之上 → 上升趋势
        if short_ma > medium_ma > long_ma and close > short_ma:
            return "bullish"
        # 空头排列 + 价格在短期均线之下 → 下降趋势
        elif short_ma < medium_ma < long_ma and close < short_ma:
            return "bearish"
        else:
            return "neutral"

    def _detect_macd_crossover(self, df: pd.DataFrame) -> str:
        if len(df) < 2:
            return "none"

        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]

        if prev_row["MACD"] <= prev_row["MACD_Signal"] and last_row["MACD"] > last_row["MACD_Signal"]:
            return "golden_cross"
        elif prev_row["MACD"] >= prev_row["MACD_Signal"] and last_row["MACD"] < last_row["MACD_Signal"]:
            return "death_cross"
        else:
            return "none"

    def _detect_rsi_status(self, rsi: float, config: dict) -> str:
        if rsi < config["oversold"]:
            return "oversold"
        elif rsi > config["overbought"]:
            return "overbought"
        else:
            return "normal"

    def _detect_bollinger_position(self, row: pd.Series) -> str:
        close = row["close"]
        upper = row["BB_Upper"]
        middle = row["BB_Middle"]
        lower = row["BB_Lower"]

        if close >= upper:
            return "above_upper"
        elif close <= lower:
            return "below_lower"
        elif close > middle:
            return "above_middle"
        else:
            return "below_middle"
