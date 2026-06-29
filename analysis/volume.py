from data.kline_data import get_candles
from data.indicators import add_indicators


def make_volume_item(score, status, reason, risk=0):
    return {
        "name": "成交量",
        "category": "成交量",
        "score": score,
        "status": status,
        "reason": reason,
        "risk": risk,
    }


def analyze_volume(data):
    """
    成交量分析模組。

    目的：
    判斷目前價格變動是否有成交量支持。
    """

    current = data.iloc[-1]
    previous = data.iloc[-2]

    current_volume = current["volume"]
    previous_volume = previous["volume"]
    average_volume_20 = data["volume"].tail(20).mean()

    current_close = current["close"]
    previous_close = previous["close"]

    price_change_percent = (
        (current_close - previous_close) / previous_close
    ) * 100

    volume_ratio = current_volume / average_volume_20 if average_volume_20 else 0

    # 價格上漲，成交量明顯放大
    if price_change_percent > 0 and volume_ratio >= 1.5:
        return make_volume_item(
            score=2,
            status="放量上漲",
            reason=(
                f"價格上漲 {price_change_percent:.2f}%，"
                f"成交量為近 20 根平均的 {volume_ratio:.2f} 倍，"
                "多方推動力較強。"
            ),
        )

    # 價格下跌，成交量明顯放大
    if price_change_percent < 0 and volume_ratio >= 1.5:
        return make_volume_item(
            score=-2,
            status="放量下跌",
            reason=(
                f"價格下跌 {abs(price_change_percent):.2f}%，"
                f"成交量為近 20 根平均的 {volume_ratio:.2f} 倍，"
                "空方賣壓較強。"
            ),
        )

    # 價格上漲，但成交量不足
    if price_change_percent > 0 and volume_ratio < 0.8:
        return make_volume_item(
            score=0,
            status="量縮上漲",
            reason=(
                f"價格上漲 {price_change_percent:.2f}%，"
                f"但成交量只有近 20 根平均的 {volume_ratio:.2f} 倍，"
                "上漲力道不足，需防回落。"
            ),
            risk=1,
        )

    # 價格下跌，但成交量不足
    if price_change_percent < 0 and volume_ratio < 0.8:
        return make_volume_item(
            score=0,
            status="量縮下跌",
            reason=(
                f"價格下跌 {abs(price_change_percent):.2f}%，"
                f"但成交量只有近 20 根平均的 {volume_ratio:.2f} 倍，"
                "下跌力道不足，需防反彈。"
            ),
            risk=1,
        )

    # 成交量接近平均
    return make_volume_item(
        score=0,
        status="成交量普通",
        reason=(
            f"目前成交量為近 20 根平均的 {volume_ratio:.2f} 倍，"
            "尚未出現明顯放量訊號。"
        ),
    )


if __name__ == "__main__":
    candles = get_candles(symbol="BTC-USDT-SWAP", bar="15m", limit=100)
    candles = candles[candles["confirm"] == "1"].copy()

    data = add_indicators(candles)
    result = analyze_volume(data)

    print("\n" + "=" * 72)
    print("BTC 永續合約｜15 分鐘成交量分析")
    print("=" * 72)
    print(f"分類：{result['category']}")
    print(f"項目：{result['name']}")
    print(f"狀態：{result['status']}")
    print(f"分數：{result['score']:+d}")
    print(f"風險：{result['risk']}")
    print(f"原因：{result['reason']}")
    print("=" * 72)