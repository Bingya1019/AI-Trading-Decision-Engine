from core.brain import analyze_brain


def format_score(score):
    if score > 0:
        return f"+{score}"
    return str(score)


def format_score_item(item):
    return (
        f"・{item['category']} / {item['name']}｜"
        f"{format_score(item['score'])} 分｜"
        f"{item['status']}｜"
        f"風險 {item['risk']}｜"
        f"{item['reason']}"
    )


def generate_brain_report(symbol="BTC-USDT-SWAP", bar="15m"):
    result = analyze_brain(symbol=symbol, bar=bar)
    coin = result["symbol"].replace("-USDT-SWAP", "")

    lines = []

    lines.append("=" * 72)
    lines.append(f"{coin} 永續合約｜{result['bar']} Brain 交易決策報告")
    lines.append("=" * 72)
    lines.append(f"判斷時間：{result['time'].strftime('%Y/%m/%d %H:%M')}")
    lines.append(f"收盤價格：{result['price']:,.6f}")
    lines.append("-" * 72)
    lines.append("【核心結論】")
    lines.append(f"方向：{result['direction']}｜強度：{result['strength']}")
    lines.append(f"可信度：{result['confidence']}%")
    lines.append(f"風險：{result['risk_stars']}｜風險分數：{result['risk_score']}")
    lines.append(f"總分：{format_score(result['total_score'])}")
    lines.append("-" * 72)
    lines.append("【分項評分】")

    for item in result["score_items"]:
        lines.append(format_score_item(item))

    lines.append("-" * 72)
    lines.append("【建議動作】")
    lines.append(result["action"])
    lines.append("=" * 72)

    return "\n".join(lines)


if __name__ == "__main__":
    report = generate_brain_report("BTC-USDT-SWAP", "15m")
    print("\n" + report)