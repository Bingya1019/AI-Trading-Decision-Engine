import pandas as pd
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

from data.kline_data import get_candles


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["ema20"] = EMAIndicator(close=df["close"], window=20).ema_indicator()
    df["ema60"] = EMAIndicator(close=df["close"], window=60).ema_indicator()

    df["rsi14"] = RSIIndicator(close=df["close"], window=14).rsi()

    macd = MACD(close=df["close"], window_slow=26, window_fast=12, window_sign=9)
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_hist"] = macd.macd_diff()

    boll = BollingerBands(close=df["close"], window=20, window_dev=2)
    df["boll_mid"] = boll.bollinger_mavg()
    df["boll_high"] = boll.bollinger_hband()
    df["boll_low"] = boll.bollinger_lband()

    return df


if __name__ == "__main__":
    candles = get_candles(symbol="BTC-USDT-SWAP", bar="15m", limit=100)
    candles = candles[candles["confirm"] == "1"]

    result = add_indicators(candles)

    print("\n" + "=" * 80)
    print("BTC 永續合約｜15 分鐘技術指標（最近 10 根已收線 K 棒）")
    print("=" * 80)

    for _, row in result.tail(10).iterrows():
        print(
            f"{row['timestamp'].strftime('%m/%d %H:%M')}｜"
            f"收盤 {row['close']:,.2f}｜"
            f"EMA20 {row['ema20']:,.2f}｜"
            f"EMA60 {row['ema60']:,.2f}｜"
            f"RSI {row['rsi14']:.2f}｜"
            f"MACD柱 {row['macd_hist']:.2f}｜"
            f"布林 {row['boll_low']:,.2f}～{row['boll_high']:,.2f}"
        )

    print("=" * 80)