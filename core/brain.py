from data.kline_data import get_candles
from data.indicators import add_indicators

from core.pipeline import run_pipeline
from core.brain_rules import evaluate_smc_rules
from core.smc_state import analyze_smc_state


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


def state_direction_to_chinese(direction):
    """
    將 State Machine 方向轉為中文。
    """
    if direction == "bullish":
        return "偏多"

    if direction == "bearish":
        return "偏空"

    return "觀望"


def decide_final_direction(
    score_direction,
    smc_direction,
    state_direction,
):
    """
    綜合判斷最終方向。

    優先順序：
    1. SMC 規則方向與流程方向一致
    2. 傳統分數與 SMC 方向一致
    3. 傳統分數與流程方向一致
    4. 僅有單一方向時保留
    5. 明顯衝突時觀望
    """
    directions = [
        direction
        for direction in [
            score_direction,
            smc_direction,
            state_direction,
        ]
        if direction != "觀望"
    ]

    if not directions:
        return "觀望"

    bullish_count = directions.count("偏多")
    bearish_count = directions.count("偏空")

    if bullish_count >= 2:
        return "偏多"

    if bearish_count >= 2:
        return "偏空"

    if len(directions) == 1:
        return directions[0]

    return "觀望"


def decide_action(
    final_direction,
    risk_score,
    smc_result,
    state_result,
):
    """
    綜合 SMC 規則與流程狀態產生行動建議。
    """
    primary_state = state_result["primary"]

    state_direction = primary_state["direction"]
    completed_count = primary_state["completed_count"]
    entry_ready = primary_state["entry_ready"]

    if entry_ready:
        return state_result["action"]

    if (
        state_direction != "neutral"
        and completed_count >= 4
    ):
        return state_result["action"]

    if smc_result["direction"] != "觀望":
        return smc_result["action"]

    if final_direction == "偏多":
        if risk_score >= 3:
            return (
                "分數方向偏多，但 SMC 流程仍未完整，"
                "且目前風險偏高；等待回踩與低週期轉強後再觀察。"
            )

        return (
            "分數條件偏多，但 SMC 共振與流程尚未完整；"
            "等待回踩與低週期轉強確認。"
        )

    if final_direction == "偏空":
        if risk_score >= 3:
            return (
                "分數方向偏空，但 SMC 流程仍未完整，"
                "且目前風險偏高；避免追空，等待反彈後再觀察。"
            )

        return (
            "分數條件偏空，但 SMC 共振與流程尚未完整；"
            "等待反彈與低週期轉弱確認。"
        )

    return (
        "傳統分數、SMC 共振與流程狀態尚未明確一致，"
        "目前暫不主動進場。"
    )


def calculate_confidence(
    score_items,
    smc_result,
    state_result,
):
    """
    可信度由三部分組成：

    1. 傳統分數
    2. SMC 共振
    3. SMC 流程完成度
    """
    total_possible_score = max(
        sum(
            max(
                abs(item.get("score", 0)),
                1,
            )
            for item in score_items
        ),
        1,
    )

    total_score = sum(
        item.get("score", 0)
        for item in score_items
    )

    score_confidence = int(
        (
            abs(total_score)
            / total_possible_score
        )
        * 100
    )

    smc_points = abs(
        smc_result["net_points"]
    )

    smc_confidence = min(
        smc_points * 7,
        95,
    )

    primary_state = state_result["primary"]

    state_confidence = int(
        primary_state["progress"]
        * 100
    )

    confidence = int(
        score_confidence * 0.25
        + smc_confidence * 0.45
        + state_confidence * 0.30
    )

    if confidence < 30:
        confidence = 30

    if smc_result["warnings"]:
        confidence -= min(
            len(smc_result["warnings"]) * 5,
            15,
        )

    if (
        primary_state["direction"] == "neutral"
        and primary_state["completed_count"] > 0
    ):
        confidence -= 5

    return max(
        20,
        min(confidence, 95),
    )


def analyze_brain(
    symbol="BTC-USDT-SWAP",
    bar="15m",
    limit=200,
):
    candles = get_candles(
        symbol=symbol,
        bar=bar,
        limit=limit,
    )

    candles = candles[
        candles["confirm"] == "1"
    ].copy()

    if len(candles) < 3:
        raise ValueError(
            "已完成的 K 棒資料不足，無法執行 Brain 分析。"
        )

    data = add_indicators(candles)
    current = data.iloc[-1]

    price = float(current["close"])

    score_items = run_pipeline(data)

    total_score = sum(
        item.get("score", 0)
        for item in score_items
    )

    risk_score = sum(
        item.get("risk", 0)
        for item in score_items
    )

    score_direction = decide_direction(
        total_score
    )

    smc_result = evaluate_smc_rules(
        score_items
    )

    state_result = analyze_smc_state(
        score_items=score_items,
        price=price,
    )

    state_direction = state_direction_to_chinese(
        state_result["primary"]["direction"]
    )

    final_direction = decide_final_direction(
        score_direction=score_direction,
        smc_direction=smc_result["direction"],
        state_direction=state_direction,
    )

    confidence = calculate_confidence(
        score_items=score_items,
        smc_result=smc_result,
        state_result=state_result,
    )

    action = decide_action(
        final_direction=final_direction,
        risk_score=risk_score,
        smc_result=smc_result,
        state_result=state_result,
    )

    return {
        "symbol": symbol,
        "bar": bar,
        "time": current["timestamp"],
        "price": price,
        "score_items": score_items,
        "total_score": total_score,
        "score_direction": score_direction,
        "direction": final_direction,
        "strength": score_to_stars(
            total_score
        ),
        "risk_score": risk_score,
        "risk_stars": risk_to_stars(
            risk_score
        ),
        "confidence": confidence,
        "action": action,
        "smc": smc_result,
        "smc_state": state_result,
        "raw": {
            "ema20": float(current["ema20"]),
            "ema60": float(current["ema60"]),
            "rsi": float(current["rsi14"]),
            "macd_hist": float(
                current["macd_hist"]
            ),
            "boll_high": float(
                current["boll_high"]
            ),
            "boll_mid": float(
                current["boll_mid"]
            ),
            "boll_low": float(
                current["boll_low"]
            ),
            "volume": float(
                current["volume"]
            ),
        },
    }


def print_state_steps(primary_state):
    """
    顯示 SMC 主流程步驟。
    """
    if primary_state["direction"] == "neutral":
        print("・目前多空流程完成度相近，尚無明確主流程。")
        return

    for step in primary_state["steps"]:
        mark = "✓" if step["completed"] else "□"

        print(
            f"{mark} Step {step['step']}｜"
            f"{step['name']}｜"
            f"{step['description']}"
        )


if __name__ == "__main__":
    result = analyze_brain(
        "BTC-USDT-SWAP",
        "15m",
    )

    coin = result["symbol"].replace(
        "-USDT-SWAP",
        "",
    )

    smc = result["smc"]
    state_result = result["smc_state"]
    primary_state = state_result["primary"]

    print("\n" + "=" * 72)
    print(
        f"{coin} 永續合約｜"
        f"{result['bar']} Smart Money Brain V4.1"
    )
    print("=" * 72)

    print(
        "判斷時間："
        f"{result['time'].strftime('%Y/%m/%d %H:%M')}"
    )

    print(
        f"收盤價格：{result['price']:,.6f}"
    )

    print("-" * 72)
    print("【核心結論】")

    print(
        f"最終方向：{result['direction']}｜"
        f"傳統分數方向：{result['score_direction']}｜"
        f"SMC 方向：{smc['direction']}｜"
        f"流程方向：{primary_state['direction_text']}"
    )

    print(
        f"可信度：{result['confidence']}%"
    )

    print(
        f"風險：{result['risk_stars']}｜"
        f"風險分數：{result['risk_score']}"
    )

    print(
        f"傳統總分：{result['total_score']:+d}"
    )

    print("-" * 72)
    print("【SMC 共振】")

    print(
        f"多方點數：{smc['bullish_points']}｜"
        f"空方點數：{smc['bearish_points']}｜"
        f"淨點數：{smc['net_points']:+d}"
    )

    print(
        f"共振等級：{smc['confluence_stars']}"
    )

    if smc["matched_rules"]:
        for rule in smc["matched_rules"]:
            print(
                f"・{rule['title']}｜"
                f"{rule['description']}"
            )
    else:
        print(
            "・目前尚無完整 SMC 共振規則成立。"
        )

    if smc["warnings"]:
        print("-" * 72)
        print("【結構警告】")

        for warning in smc["warnings"]:
            print(f"・{warning}")

    print("-" * 72)
    print("【SMC 流程狀態】")

    print(
        f"主流程：{primary_state['direction_text']}｜"
        f"完成度："
        f"{primary_state['completed_count']}/"
        f"{primary_state['total_steps']}｜"
        f"{primary_state['progress'] * 100:.0f}%"
    )

    print_state_steps(
        primary_state
    )

    print("-" * 72)
    print("【多空流程比較】")

    bullish_state = state_result["bullish"]
    bearish_state = state_result["bearish"]

    print(
        "多方流程："
        f"{bullish_state['completed_count']}/"
        f"{bullish_state['total_steps']}｜"
        f"{bullish_state['progress'] * 100:.0f}%"
    )

    print(
        "空方流程："
        f"{bearish_state['completed_count']}/"
        f"{bearish_state['total_steps']}｜"
        f"{bearish_state['progress'] * 100:.0f}%"
    )

    print("-" * 72)
    print("【分項評分】")

    for item in result["score_items"]:
        print(
            f"・{item['category']} / "
            f"{item['name']}｜"
            f"{item['score']:+d} 分｜"
            f"{item['status']}｜"
            f"風險 {item['risk']}｜"
            f"{item['reason']}"
        )

    print("-" * 72)
    print(f"建議動作：{result['action']}")
    print("=" * 72)