from data.kline_data import get_candles
from data.indicators import add_indicators
from analysis.swing import find_swings
from analysis.structure import classify_swings
from analysis.trend_state import analyze_trend_state


def make_choch_item(score, status, reason, risk=0, details=None):
    return {
        "name": "CHOCH",
        "category": "市場結構反轉",
        "score": score,
        "status": status,
        "reason": reason,
        "risk": risk,
        "details": details or {},
    }


def find_last_label(classified_swings, label):
    """
    尋找最近一個指定的結構點，例如 HL 或 LH。
    """
    matches = [
        item
        for item in classified_swings
        if item["label"] == label
    ]

    return matches[-1] if matches else None


def build_previous_structure(data):
    """
    使用最新 K 棒之前的歷史資料建立結構快照。

    CHOCH 要判斷的是：
    原本的趨勢，是否被最新收盤價破壞。
    """
    history = data.iloc[:-1].copy()

    swings = find_swings(history)
    classified_swings = classify_swings(swings)
    trend_result = analyze_trend_state(history)

    return {
        "trend": trend_result["trend"],
        "trend_status": trend_result["status"],
        "classified_swings": classified_swings,
        "last_hl": find_last_label(classified_swings, "HL"),
        "last_lh": find_last_label(classified_swings, "LH"),
    }


def analyze_choch(data):
    """
    CHOCH V1 判斷規則：

    CHOCH Down：
    1. 原本趨勢為 Bull
    2. 前一根收盤尚未跌破最近 HL
    3. 最新收盤由上往下跌破最近 HL

    CHOCH Up：
    1. 原本趨勢為 Bear
    2. 前一根收盤尚未突破最近 LH
    3. 最新收盤由下往上突破最近 LH

    Range 狀態不判斷 CHOCH。
    """
    if len(data) < 10:
        return make_choch_item(
            score=0,
            status="資料不足",
            reason="目前 K 棒資料不足，無法可靠判斷 CHOCH。",
            risk=1,
            details={},
        )

    structure = build_previous_structure(data)

    previous = data.iloc[-2]
    current = data.iloc[-1]

    previous_close = previous["close"]
    current_close = current["close"]
    current_time = current["timestamp"]

    previous_trend = structure["trend"]
    last_hl = structure["last_hl"]
    last_lh = structure["last_lh"]

    details = {
        "previous_trend": previous_trend,
        "previous_close": previous_close,
        "current_close": current_close,
        "event_time": current_time,
        "last_hl": last_hl,
        "last_lh": last_lh,
        "break_level": None,
        "direction": None,
    }

    # 原本多頭，最新收盤跌破最近 HL
    if previous_trend == "bull":
        if last_hl is None:
            return make_choch_item(
                score=0,
                status="尚無 CHOCH Down",
                reason="原本為 Bull 結構，但目前沒有可供跌破確認的 HL。",
                details=details,
            )

        hl_price = last_hl["price"]

        if previous_close >= hl_price > current_close:
            details["break_level"] = hl_price
            details["direction"] = "down"

            return make_choch_item(
                score=-3,
                status="CHOCH Down",
                reason=(
                    f"原本市場為 Bull 結構，但最新收盤價 "
                    f"{current_close:,.2f} 正式跌破最近 HL "
                    f"{hl_price:,.2f}，多頭結構遭到破壞，"
                    "市場可能轉為空頭或進入反轉階段。"
                ),
                risk=2,
                details=details,
            )

        return make_choch_item(
            score=0,
            status="尚無 CHOCH Down",
            reason=(
                f"原本市場為 Bull，最新收盤價 {current_close:,.2f} "
                f"尚未由上往下跌破最近 HL {hl_price:,.2f}。"
            ),
            details=details,
        )

    # 原本空頭，最新收盤突破最近 LH
    if previous_trend == "bear":
        if last_lh is None:
            return make_choch_item(
                score=0,
                status="尚無 CHOCH Up",
                reason="原本為 Bear 結構，但目前沒有可供突破確認的 LH。",
                details=details,
            )

        lh_price = last_lh["price"]

        if previous_close <= lh_price < current_close:
            details["break_level"] = lh_price
            details["direction"] = "up"

            return make_choch_item(
                score=3,
                status="CHOCH Up",
                reason=(
                    f"原本市場為 Bear 結構，但最新收盤價 "
                    f"{current_close:,.2f} 正式突破最近 LH "
                    f"{lh_price:,.2f}，空頭結構遭到破壞，"
                    "市場可能轉為多頭或進入反轉階段。"
                ),
                risk=2,
                details=details,
            )

        return make_choch_item(
            score=0,
            status="尚無 CHOCH Up",
            reason=(
                f"原本市場為 Bear，最新收盤價 {current_close:,.2f} "
                f"尚未由下往上突破最近 LH {lh_price:,.2f}。"
            ),
            details=details,
        )

    return make_choch_item(
        score=0,
        status="不判斷 CHOCH",
        reason="原本趨勢狀態為 Range，暫時不判定市場結構反轉。",
        risk=1,
        details=details,
    )


def format_structure_point(point):
    if point is None:
        return "無資料"

    return (
        f"{point['label']}｜"
        f"{point['price']:,.2f}｜"
        f"{point['time'].strftime('%m/%d %H:%M')}"
    )


if __name__ == "__main__":
    candles = get_candles(
        symbol="BTC-USDT-SWAP",
        bar="15m",
        limit=150,
    )

    candles = candles[candles["confirm"] == "1"].copy()
    data = add_indicators(candles)

    result = analyze_choch(data)
    details = result["details"]

    print("\n" + "=" * 72)
    print("BTC 永續合約｜15 分鐘 CHOCH 分析 V1")
    print("=" * 72)
    print(f"原本趨勢：{details.get('previous_trend', '未知')}")
    print(f"前一收盤：{details.get('previous_close', 0):,.2f}")
    print(f"最新收盤：{details.get('current_close', 0):,.2f}")
    print(f"最近 HL：{format_structure_point(details.get('last_hl'))}")
    print(f"最近 LH：{format_structure_point(details.get('last_lh'))}")
    print("-" * 72)
    print(f"狀態：{result['status']}")
    print(f"分數：{result['score']:+d}")
    print(f"風險：{result['risk']}")
    print(f"原因：{result['reason']}")
    print("=" * 72)