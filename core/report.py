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


def format_smc_rule(rule):
    return (
        f"・{rule['title']}｜"
        f"權重 {rule['weight']}｜"
        f"{rule['description']}"
    )


def format_state_step(step):
    mark = "✓" if step["completed"] else "□"

    return (
        f"{mark} Step {step['step']}｜"
        f"{step['name']}｜"
        f"{step['description']}"
    )


def format_zone(name, zone):
    if zone is None:
        return f"{name}：無有效區域"

    return (
        f"{name}："
        f"{zone['low']:,.2f}～"
        f"{zone['high']:,.2f}｜"
        f"中間價 {zone['midpoint']:,.2f}"
    )


def generate_brain_report(
    symbol="BTC-USDT-SWAP",
    bar="15m",
):
    result = analyze_brain(
        symbol=symbol,
        bar=bar,
    )

    coin = result["symbol"].replace(
        "-USDT-SWAP",
        "",
    )

    smc = result["smc"]
    state_result = result["smc_state"]
    primary_state = state_result["primary"]

    lines = []

    lines.append("=" * 72)

    lines.append(
        f"{coin} 永續合約｜"
        f"{result['bar']} Smart Money Brain V4.1"
    )

    lines.append("=" * 72)

    lines.append(
        "判斷時間："
        f"{result['time'].strftime('%Y/%m/%d %H:%M')}"
    )

    lines.append(
        f"收盤價格：{result['price']:,.6f}"
    )

    lines.append("-" * 72)
    lines.append("【核心結論】")

    lines.append(
        f"最終方向：{result['direction']}｜"
        f"強度：{result['strength']}"
    )

    lines.append(
        f"傳統分數方向：{result['score_direction']}｜"
        f"SMC 方向：{smc['direction']}｜"
        f"流程方向：{primary_state['direction_text']}"
    )

    lines.append(
        f"可信度：{result['confidence']}%"
    )

    lines.append(
        f"風險：{result['risk_stars']}｜"
        f"風險分數：{result['risk_score']}"
    )

    lines.append(
        "傳統總分："
        f"{format_score(result['total_score'])}"
    )

    lines.append("-" * 72)
    lines.append("【SMC 共振判斷】")

    lines.append(
        f"多方共振：{smc['bullish_rule_count']} 項｜"
        f"點數 {smc['bullish_points']}"
    )

    lines.append(
        f"空方共振：{smc['bearish_rule_count']} 項｜"
        f"點數 {smc['bearish_points']}"
    )

    lines.append(
        "SMC 淨點數："
        f"{format_score(smc['net_points'])}"
    )

    lines.append(
        f"共振等級：{smc['confluence_stars']}"
    )

    if smc["matched_rules"]:
        lines.append("")
        lines.append("成立規則：")

        for rule in smc["matched_rules"]:
            lines.append(
                format_smc_rule(rule)
            )
    else:
        lines.append(
            "・目前尚無完整 SMC 共振規則成立。"
        )

    if smc["warnings"]:
        lines.append("-" * 72)
        lines.append("【結構警告】")

        for warning in smc["warnings"]:
            lines.append(
                f"・{warning}"
            )

    lines.append("-" * 72)
    lines.append("【SMC 流程狀態】")

    lines.append(
        f"主流程：{primary_state['direction_text']}｜"
        f"完成度："
        f"{primary_state['completed_count']}/"
        f"{primary_state['total_steps']}｜"
        f"{primary_state['progress'] * 100:.0f}%"
    )

    if primary_state["direction"] == "neutral":
        lines.append(
            "・目前多空流程完成度相近，尚無明確主流程。"
        )
    else:
        for step in primary_state["steps"]:
            lines.append(
                format_state_step(step)
            )

    lines.append("")
    lines.append(
        "流程建議："
        f"{state_result['action']}"
    )

    lines.append("-" * 72)
    lines.append("【多空流程比較】")

    bullish_state = state_result["bullish"]
    bearish_state = state_result["bearish"]

    lines.append(
        "多方流程："
        f"{bullish_state['completed_count']}/"
        f"{bullish_state['total_steps']}｜"
        f"{bullish_state['progress'] * 100:.0f}%"
    )

    lines.append(
        "空方流程："
        f"{bearish_state['completed_count']}/"
        f"{bearish_state['total_steps']}｜"
        f"{bearish_state['progress'] * 100:.0f}%"
    )

    lines.append("-" * 72)
    lines.append("【主流程區域】")

    zones = primary_state["zones"]

    lines.append(
        format_zone(
            "Order Block",
            zones.get("order_block"),
        )
    )

    lines.append(
        format_zone(
            "Fair Value Gap",
            zones.get("fvg"),
        )
    )

    lines.append("-" * 72)
    lines.append("【模組方向】")

    module_directions = smc[
        "module_directions"
    ]

    lines.append(
        "Trend："
        f"{module_directions['trend']}｜"
        "BOS："
        f"{module_directions['bos']}｜"
        "CHOCH："
        f"{module_directions['choch']}"
    )

    lines.append(
        "Liquidity："
        f"{module_directions['liquidity']}｜"
        "Order Block："
        f"{module_directions['order_block']}｜"
        "FVG："
        f"{module_directions['fvg']}"
    )

    lines.append("-" * 72)
    lines.append("【分項評分】")

    for item in result["score_items"]:
        lines.append(
            format_score_item(item)
        )

    lines.append("-" * 72)
    lines.append("【建議動作】")
    lines.append(result["action"])
    lines.append("=" * 72)

    return "\n".join(lines)


if __name__ == "__main__":
    report = generate_brain_report(
        "BTC-USDT-SWAP",
        "15m",
    )

    print("\n" + report)