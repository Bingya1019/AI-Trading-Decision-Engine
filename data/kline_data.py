import requests
import pandas as pd


def get_candles(symbol="BTC-USDT-SWAP", bar="15m", limit=100):
    """
    從 OKX 取得永續合約 K 線資料。

    symbol：交易對，例如 BTC-USDT-SWAP
    bar：K 線週期，例如 1m、5m、15m、1H、4H
    limit：抓取根數，最多 300 根
    """
    url = "https://www.okx.com/api/v5/market/candles"

    params = {
        "instId": symbol,
        "bar": bar,
        "limit": limit,
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    result = response.json()

    if result["code"] != "0":
        raise RuntimeError(f"OKX K 線抓取失敗：{result}")

    columns = [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "volume_ccy",
        "volume_quote",
        "confirm",
    ]

    df = pd.DataFrame(result["data"], columns=columns)

    # OKX 回傳最新 K 線在最上面，改成時間由舊到新
    df = df.iloc[::-1].reset_index(drop=True)

    df["timestamp"] = pd.to_datetime(
        df["timestamp"].astype("int64"),
        unit="ms",
        utc=True,
    ).dt.tz_convert("Asia/Taipei")

    number_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "volume_ccy",
        "volume_quote",
    ]

    for column in number_columns:
        df[column] = pd.to_numeric(df[column])

    return df


if __name__ == "__main__":
    candles = get_candles()

    print("\n" + "=" * 90)
    print("BTC 永續合約｜15 分鐘 K 線（最近 10 根）")
    print("=" * 90)

    for _, row in candles.tail(10).iterrows():
        狀態 = "已收線" if row["confirm"] == "1" else "進行中"

        print(
            f"{row['timestamp'].strftime('%m/%d %H:%M')}｜"
            f"開 {row['open']:,.2f}｜"
            f"高 {row['high']:,.2f}｜"
            f"低 {row['low']:,.2f}｜"
            f"收 {row['close']:,.2f}｜"
            f"成交量 {row['volume']:,.2f}｜"
            f"{狀態}"
        )

    print("=" * 90)