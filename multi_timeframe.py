from strategy import analyze_strategy


def analyze_multi_timeframe(symbol="BTC-USDT-SWAP"):
    """
    多週期分析：
    4H  ：大方向
    1H  ：主要趨勢
    15m ：交易機會
    5m  ：進場時機
    """
    timeframes = [
        ("4H", "大方向"),
        ("1H", "主要趨勢"),
        ("15m", "交易機會"),
        ("5m", "進場時機"),
    ]

    results = []

    for bar, role in timeframes:
        result = analyze_strategy(symbol=symbol, bar=bar)
        result["role"] = role
        results.append(result)

    directions = [item["direction"] for item in results]
    trends = [item["trend"] for item in results]
    momentums = [item["momentum"] for item in results]

    bullish_count = directions.count("偏多")
    bearish_count = directions.count("偏空")
    wait_count = directions.count("觀望")

    # 共振判斷
    if bullish_count >= 3 and trends[0] != "偏空":
        final_direction = "偏多共振"
        action = "多數週期偏多，可優先觀察做多機會，但仍需等待 5m 出現進場訊號。"
    elif bearish_count >= 3 and trends[0] != "偏多":
        final_direction = "偏空共振"
        action = "多數週期偏空，可優先觀察做空機會，但仍需等待 5m 出現進場訊號。"
    elif trends[0] == "偏多" and trends[1] == "偏多" and directions[2] == "觀望":
        final_direction = "多頭回調"
        action = "4H 與 1H 偏多，15m 暫時觀望，可能是多頭回調，等待 5m 轉強。"
    elif trends[0] == "偏空" and trends[1] == "偏空" and directions[2] == "觀望":
        final_direction = "空頭反彈"
        action = "4H 與 1H 偏空，15m 暫時觀望，可能是空頭反彈，等待 5m 轉弱。"
    else:
        final_direction = "多空不一致"
        action = "多週期方向尚未共振，暫時不主動進場。"

    return {
        "symbol": symbol,
        "results": results,
        "bullish_count": bullish_count,
        "bearish_count": bearish_count,
        "wait_count": wait_count,
        "final_direction": final_direction,
        "action": action,
        "directions": directions,
        "trends": trends,
        "momentums": momentums,
    }


if __name__ == "__main__":
    report = analyze_multi_timeframe("BTC-USDT-SWAP")
    coin = report["symbol"].replace("-USDT-SWAP", "")

    print("\n" + "=" * 72)
    print(f"{coin} 永續合約｜多週期共振分析")
    print("=" * 72)

    for item in report["results"]:
        print(
            f"{item['bar']:<4}｜"
            f"{item['role']:<8}｜"
            f"方向：{item['direction']}｜"
            f"趨勢：{item['trend']}｜"
            f"動能：{item['momentum']}｜"
            f"RSI：{item['rsi']:.2f}｜"
            f"價格：{item['price']:,.4f}"
        )

    print("-" * 72)
    print(f"偏多數量：{report['bullish_count']}")
    print(f"偏空數量：{report['bearish_count']}")
    print(f"觀望數量：{report['wait_count']}")
    print("-" * 72)
    print(f"多週期結論：{report['final_direction']}")
    print(f"建議動作：{report['action']}")
    print("=" * 72)