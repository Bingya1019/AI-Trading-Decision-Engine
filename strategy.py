from core.brain import analyze_brain


def analyze_strategy(symbol="BTC-USDT-SWAP", bar="15m"):
    brain_result = analyze_brain(symbol=symbol, bar=bar)

    reasons = [
        f"{item['category']} / {item['name']}："
        f"{item['score']:+d} 分，{item['status']}。{item['reason']}"
        for item in brain_result["score_items"]
    ]

    raw = brain_result["raw"]

    return {
        "symbol": brain_result["symbol"],
        "bar": brain_result["bar"],
        "time": brain_result["time"],
        "price": brain_result["price"],

        "score": brain_result["total_score"],
        "strength": brain_result["strength"],
        "confidence": brain_result["confidence"],
        "risk_score": brain_result["risk_score"],
        "risk_stars": brain_result["risk_stars"],

        "direction": brain_result["direction"],
        "trend": get_category_status(brain_result, "趨勢"),
        "momentum": get_category_status(brain_result, "動能"),
        "rsi_status": get_indicator_status(brain_result, "RSI"),
        "boll_status": get_indicator_status(brain_result, "布林通道"),

        "ema20": raw["ema20"],
        "ema60": raw["ema60"],
        "rsi": raw["rsi"],
        "macd_hist": raw["macd_hist"],
        "boll_high": raw["boll_high"],
        "boll_mid": raw["boll_mid"],
        "boll_low": raw["boll_low"],

        "action": brain_result["action"],
        "reasons": reasons,
        "score_items": brain_result["score_items"],
        "raw": raw,
    }


def get_category_status(brain_result, category):
    for item in brain_result["score_items"]:
        if item["category"] == category:
            return item["status"]

    return "未知"


def get_indicator_status(brain_result, name):
    for item in brain_result["score_items"]:
        if item["name"] == name:
            return item["status"]

    return "未知"


if __name__ == "__main__":
    result = analyze_strategy("BTC-USDT-SWAP", "15m")
    coin = result["symbol"].replace("-USDT-SWAP", "")

    print("\n" + "=" * 72)
    print(f"{coin} 永續合約｜{result['bar']} 單週期策略判斷")
    print("=" * 72)
    print(f"判斷時間：{result['time'].strftime('%Y/%m/%d %H:%M')}")
    print(f"收盤價格：{result['price']:,.6f}")
    print("-" * 72)
    print(f"方向：{result['direction']}｜強度：{result['strength']}")
    print(f"可信度：{result['confidence']}%")
    print(f"風險：{result['risk_stars']}｜風險分數：{result['risk_score']}")
    print(f"總分：{result['score']}")
    print("-" * 72)
    print("判斷依據：")

    for reason in result["reasons"]:
        print(f"・{reason}")

    print("-" * 72)
    print(f"建議動作：{result['action']}")
    print("=" * 72)