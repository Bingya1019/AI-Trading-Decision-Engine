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
    尋找最近一個指定結構點，例如 HL 或 LH。
    """
    matches = [
        item
        for item in classified_swings
        if item["label"] == label
    ]

    return matches[-1] if matches else None


def build_previous_structure(data):
    """
    使用最新 K 棒以前的歷史資料建立結構快照。

    CHOCH 判斷的是：
    原本的市場趨勢，是否被最新收盤價破壞。
    """
    if len(data) < 2:
        return {
            "trend": "range",
            "trend_status": "Range",
            "classified_swings": [],
            "last_hl": None,
            "last_lh": None,
        }

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


def detect_choch_at_latest_bar(data):
    """
    判斷最新一根 K 棒是否剛發生 CHOCH。

    CHOCH Down：
    - 原本為 Bull
    - 前一根收盤尚未跌破最近 HL
    - 最新收盤由上往下跌破最近 HL

    CHOCH Up：
    - 原本為 Bear
    - 前一根收盤尚未突破最近 LH
    - 最新收盤由下往上突破最近 LH
    """
    if len(data) < 10:
        return None

    structure = build_previous_structure(data)

    previous = data.iloc[-2]
    current = data.iloc[-1]

    previous_close = previous["close"]
    current_close = current["close"]
    current_time = current["timestamp"]

    previous_trend = structure["trend"]
    last_hl = structure["last_hl"]
    last_lh = structure["last_lh"]

    if previous_trend == "bull" and last_hl is not None:
        hl_price = last_hl["price"]

        if previous_close >= hl_price > current_close:
            return {
                "event_type": "CHOCH",
                "direction": "down",
                "status": "CHOCH Down",
                "score": -3,
                "previous_trend": previous_trend,
                "break_level": hl_price,
                "break_close": current_close,
                "break_time": current_time,
                "break_index": len(data) - 1,
                "structure_point": last_hl,
            }

    if previous_trend == "bear" and last_lh is not None:
        lh_price = last_lh["price"]

        if previous_close <= lh_price < current_close:
            return {
                "event_type": "CHOCH",
                "direction": "up",
                "status": "CHOCH Up",
                "score": 3,
                "previous_trend": previous_trend,
                "break_level": lh_price,
                "break_close": current_close,
                "break_time": current_time,
                "break_index": len(data) - 1,
                "structure_point": last_lh,
            }

    return None


def find_recent_choch_event(data, lookback=80):
    """
    往回掃描最近的 CHOCH 事件。

    同一個 HL 或 LH 被重複穿越時，只記錄第一次有效事件，
    避免同一個結構點重複計算 CHOCH。
    """
    if len(data) < 10:
        return None

    start_index = max(9, len(data) - lookback)
    used_structure_points = set()
    events = []

    for end_index in range(start_index, len(data)):
        history = data.iloc[: end_index + 1].copy()
        event = detect_choch_at_latest_bar(history)

        if event is None:
            continue

        structure_point = event["structure_point"]

        structure_key = (
            event["direction"],
            structure_point["index"],
            round(float(structure_point["price"]), 8),
        )

        if structure_key in used_structure_points:
            continue

        used_structure_points.add(structure_key)

        event["bars_ago"] = len(data) - 1 - end_index
        events.append(event)

    return events[-1] if events else None


def calculate_recent_event_score(event):
    """
    最近 CHOCH 對目前總分採時間衰減：

    0 根前：完整 ±3
    1～4 根前：±2
    5～8 根前：±1
    超過 8 根：0

    CHOCH 是反轉警訊，風險仍會另外保留。
    """
    if event is None:
        return 0

    bars_ago = event["bars_ago"]
    direction = event["direction"]

    if bars_ago == 0:
        strength = 3
    elif bars_ago <= 4:
        strength = 2
    elif bars_ago <= 8:
        strength = 1
    else:
        strength = 0

    return strength if direction == "up" else -strength


def analyze_choch(data, lookback=80):
    """
    CHOCH V2：

    1. 判斷最新 K 棒是否正在發生 CHOCH。
    2. 若最新 K 棒沒有 CHOCH，追蹤最近一次 CHOCH。
    3. 最近事件採時間衰減評分。
    4. 同一個 HL／LH 只記錄一次反轉事件。
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

    current_event = detect_choch_at_latest_bar(data)
    recent_event = find_recent_choch_event(
        data=data,
        lookback=lookback,
    )

    details = {
        "previous_trend": structure["trend"],
        "previous_close": previous_close,
        "current_close": current_close,
        "last_hl": structure["last_hl"],
        "last_lh": structure["last_lh"],
        "current_event": current_event,
        "recent_event": recent_event,
        "event_time": None,
        "break_level": None,
        "break_close": None,
        "bars_ago": None,
        "direction": None,
    }

    if current_event is not None:
        details["event_time"] = current_event["break_time"]
        details["break_level"] = current_event["break_level"]
        details["break_close"] = current_event["break_close"]
        details["bars_ago"] = 0
        details["direction"] = current_event["direction"]

        if current_event["direction"] == "up":
            reason = (
                f"原本市場為 Bear 結構，但最新收盤價 "
                f"{current_event['break_close']:,.2f} 正式突破最近 LH "
                f"{current_event['break_level']:,.2f}，空頭結構遭到破壞，"
                "市場可能轉為多頭或進入反轉階段。"
            )
        else:
            reason = (
                f"原本市場為 Bull 結構，但最新收盤價 "
                f"{current_event['break_close']:,.2f} 正式跌破最近 HL "
                f"{current_event['break_level']:,.2f}，多頭結構遭到破壞，"
                "市場可能轉為空頭或進入反轉階段。"
            )

        return make_choch_item(
            score=current_event["score"],
            status=current_event["status"],
            reason=reason,
            risk=2,
            details=details,
        )

    if recent_event is not None:
        recent_score = calculate_recent_event_score(recent_event)

        details["event_time"] = recent_event["break_time"]
        details["break_level"] = recent_event["break_level"]
        details["break_close"] = recent_event["break_close"]
        details["bars_ago"] = recent_event["bars_ago"]
        details["direction"] = recent_event["direction"]

        if recent_event["direction"] == "up":
            direction_text = "由空轉多的結構反轉"
        else:
            direction_text = "由多轉空的結構反轉"

        return make_choch_item(
            score=recent_score,
            status=f"最近 {recent_event['status']}",
            reason=(
                f"最近一次為{direction_text}，發生於 "
                f"{recent_event['break_time'].strftime('%m/%d %H:%M')}；"
                f"突破價位 {recent_event['break_level']:,.2f}，"
                f"突破收盤 {recent_event['break_close']:,.2f}，"
                f"距今 {recent_event['bars_ago']} 根 K 棒。"
            ),
            risk=2 if recent_event["bars_ago"] <= 8 else 1,
            details=details,
        )

    previous_trend = structure["trend"]
    last_hl = structure["last_hl"]
    last_lh = structure["last_lh"]

    if previous_trend == "bull":
        if last_hl is None:
            reason = "原本為 Bull 結構，但目前沒有可供跌破確認的 HL。"
        else:
            reason = (
                f"原本市場為 Bull，最新收盤價 {current_close:,.2f} "
                f"尚未由上往下跌破最近 HL {last_hl['price']:,.2f}。"
            )

        return make_choch_item(
            score=0,
            status="尚無 CHOCH Down",
            reason=reason,
            risk=0,
            details=details,
        )

    if previous_trend == "bear":
        if last_lh is None:
            reason = "原本為 Bear 結構，但目前沒有可供突破確認的 LH。"
        else:
            reason = (
                f"原本市場為 Bear，最新收盤價 {current_close:,.2f} "
                f"尚未由下往上突破最近 LH {last_lh['price']:,.2f}。"
            )

        return make_choch_item(
            score=0,
            status="尚無 CHOCH Up",
            reason=reason,
            risk=0,
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


def format_recent_event(event):
    if event is None:
        return "無資料"

    return (
        f"{event['status']}｜"
        f"時間 {event['break_time'].strftime('%m/%d %H:%M')}｜"
        f"突破價位 {event['break_level']:,.2f}｜"
        f"突破收盤 {event['break_close']:,.2f}｜"
        f"距今 {event['bars_ago']} 根 K 棒"
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
    print("BTC 永續合約｜15 分鐘 CHOCH 分析 V2")
    print("=" * 72)
    print(f"原本趨勢：{details.get('previous_trend', '未知')}")
    print(f"前一收盤：{details.get('previous_close', 0):,.2f}")
    print(f"最新收盤：{details.get('current_close', 0):,.2f}")
    print(f"最近 HL：{format_structure_point(details.get('last_hl'))}")
    print(f"最近 LH：{format_structure_point(details.get('last_lh'))}")
    print(f"最近事件：{format_recent_event(details.get('recent_event'))}")
    print("-" * 72)
    print(f"狀態：{result['status']}")
    print(f"分數：{result['score']:+d}")
    print(f"風險：{result['risk']}")
    print(f"原因：{result['reason']}")
    print("=" * 72)