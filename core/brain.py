from data.kline_data import get_candles
from data.indicators import add_indicators
from core.pipeline import run_pipeline


def score_to_stars(score):
    abs_score = abs(score)

    if abs_score >= 8:
        return "★★★★★"
    elif abs_score >= 6:
        return "★★★★☆"
    elif abs_score >= 4:
        return "★★★☆☆"
    elif abs_score >= 2:
        return "★★☆☆☆"
    elif abs_score >= 1:
        return "★☆☆☆☆"
    else:
        return "☆☆☆☆☆"


def risk_to_stars(risk_score):
    if risk_score >= 5:
        return "★★★★★"
    elif risk_score >= 4:
        return "★★★★☆"
    elif risk_score >= 3:
        return "★★★☆☆"
    elif risk_score >= 2:
        return "★★☆☆☆"
    elif risk_score >= 1:
        return "★☆☆☆☆"
    else:
        return "☆☆☆☆☆"


def decide_direction(total_score):
    if total_score >= 3:
        return "偏多"

    if total_score <= -3:
        return "偏空"

    return "觀望"


def decide_action(direction, risk_score):
    if direction == "偏多":
        if risk_score >= 3:
            return "方向偏多，但風險偏高，等待回踩或 5 分鐘轉強後再觀察。"
        return "條件偏多，可等待回踩或 5 分鐘轉強後觀察做多機會。"

    if direction == "偏空":
        if risk_score >= 3:
            return "方向偏空，但風險偏高，避免追空，等待反彈後再觀察。"
        return "條件偏空，可等待反彈或 5 分鐘轉弱後觀察做空機會。"

    return "多空條件尚未明確一致，暫時不主動進場。"


def calculate_confidence(score_items):
    total_possible_score = 11
    total_score = sum(item["score"] for item in score_items)
    abs_score = abs(total_score)

    confidence = int((abs_score / total_possible_score) * 100)

    if confidence < 30:
        confidence = 30

    return min(confidence, 95)


def analyze_brain(symbol="BTC-USDT-SWAP", bar="15m", limit=200):
    candles = get_candles(symbol=symbol, bar=bar, limit=limit)
    candles = candles[candles["confirm"] == "1"].copy()

    data = add_indicators(candles)
    current = data.iloc[-1]

    score_items = run_pipeline(data)

    total_score = sum(item["score"] for item in score_items)
    risk_score = sum(item["risk"] for item in score_items)
    direction = decide_direction(total_score)
    confidence = calculate_confidence(score_items)
    action = decide_action(direction, risk_score)

    return {
        "symbol": symbol,
        "bar": bar,
        "time": current["timestamp"],
        "price": current["close"],
        "score_items": score_items,
        "total_score": total_score,
        "direction": direction,
        "strength": score_to_stars(total_score),
        "risk_score": risk_score,
        "risk_stars": risk_to_stars(risk_score),
        "confidence": confidence,
        "action": action,
        "raw": {
            "ema20": current["ema20"],
            "ema60": current["ema60"],
            "rsi": current["rsi14"],
            "macd_hist": current["macd_hist"],
            "boll_high": current["boll_high"],
            "boll_mid": current["boll_mid"],
            "boll_low": current["boll_low"],
            "volume": current["volume"],
        },
    }


if __name__ == "__main__":
    result = analyze_brain("BTC-USDT-SWAP", "15m")
    coin = result["symbol"].replace("-USDT-SWAP", "")

    print("\n" + "=" * 72)
    print(f"{coin} 永續合約｜{result['bar']} Brain 交易大腦分析")
    print("=" * 72)
    print(f"判斷時間：{result['time'].strftime('%Y/%m/%d %H:%M')}")
    print(f"收盤價格：{result['price']:,.6f}")
    print("-" * 72)
    print(f"方向：{result['direction']}｜強度：{result['strength']}")
    print(f"可信度：{result['confidence']}%")
    print(f"風險：{result['risk_stars']}｜風險分數：{result['risk_score']}")
    print(f"總分：{result['total_score']}")
    print("-" * 72)
    print("分項評分：")

    for item in result["score_items"]:
        print(
            f"・{item['category']} / {item['name']}｜"
            f"{item['score']:+d} 分｜"
            f"{item['status']}｜"
            f"風險 {item['risk']}｜"
            f"{item['reason']}"
        )

    print("-" * 72)
    print(f"建議動作：{result['action']}")
    print("=" * 72)