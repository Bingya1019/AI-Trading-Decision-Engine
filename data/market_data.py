import requests
from datetime import datetime

# 要追蹤的永續合約交易對
symbols = [
    "BTC-USDT-SWAP",
    "ETH-USDT-SWAP",
    "SOL-USDT-SWAP",
    "XRP-USDT-SWAP",
    "DOGE-USDT-SWAP",
    "HYPE-USDT-SWAP",
]


def get_swap_tickers():
    """取得 OKX 所有 USDT 永續合約行情。"""
    url = "https://www.okx.com/api/v5/market/tickers"
    params = {"instType": "SWAP"}

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    if data["code"] != "0":
        raise RuntimeError(f"抓取 OKX 永續合約行情失敗：{data}")

    return {item["instId"]: item for item in data["data"]}


if __name__ == "__main__":
    tickers = get_swap_tickers()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("\n" + "=" * 70)
    print(f"OKX 永續合約即時行情｜更新時間：{now}")
    print("=" * 70)

    for symbol in symbols:
        ticker = tickers.get(symbol)

        if not ticker:
            print(f"{symbol}｜找不到行情資料")
            continue

        last_price = float(ticker["last"])
        open_24h = float(ticker["open24h"])
        change_percent = ((last_price - open_24h) / open_24h) * 100 if open_24h else 0
        volume_24h = float(ticker["volCcy24h"])
        coin = symbol.replace("-USDT-SWAP", "")

        print(
            f"{coin} 永續合約｜"
            f"最新價 {last_price:,.6f}｜"
            f"24 小時漲跌 {change_percent:+.2f}%｜"
            f"24 小時成交量 {volume_24h:,.2f} USDT"
        )

    print("=" * 70)