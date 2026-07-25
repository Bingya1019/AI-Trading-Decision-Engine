def make_event_item(
    name,
    category,
    score,
    status,
    reason,
    risk=0,
    details=None,
):
    """
    建立統一格式的事件分析結果。

    所有事件模組，例如 BOS、CHOCH、Liquidity Sweep，
    最後都使用相同格式回傳。
    """
    return {
        "name": name,
        "category": category,
        "score": score,
        "status": status,
        "reason": reason,
        "risk": risk,
        "details": details or {},
    }


def find_last_label(classified_swings, label):
    """
    從已分類的 Swing 結構中，
    尋找最近一個指定標籤。

    例如：
    HH、HL、LH、LL
    """
    matches = [
        item
        for item in classified_swings
        if item.get("label") == label
    ]

    return matches[-1] if matches else None


def calculate_recent_event_score(
    event,
    full_score=3,
    recent_score=2,
    fading_score=1,
    recent_bars=4,
    fading_bars=8,
):
    """
    根據事件距離現在的 K 棒數量，
    計算時間衰減後的分數。

    預設規則：

    0 根前：
    ±3

    1～4 根前：
    ±2

    5～8 根前：
    ±1

    超過 8 根：
    0

    event 必須包含：
    - bars_ago
    - direction
    """
    if event is None:
        return 0

    bars_ago = event.get("bars_ago")
    direction = event.get("direction")

    if bars_ago is None or direction not in {"up", "down"}:
        return 0

    if bars_ago == 0:
        strength = full_score
    elif bars_ago <= recent_bars:
        strength = recent_score
    elif bars_ago <= fading_bars:
        strength = fading_score
    else:
        strength = 0

    return strength if direction == "up" else -strength


def build_structure_key(event):
    """
    建立事件去重用的識別碼。

    同一個結構點如果被價格重複穿越，
    只保留第一次有效事件。

    優先使用：
    - direction
    - structure point index
    - structure point price

    若事件沒有 structure_point，
    則退回使用事件本身的價位與時間。
    """
    direction = event.get("direction")
    structure_point = event.get("structure_point")

    if structure_point is not None:
        return (
            direction,
            structure_point.get("index"),
            round(float(structure_point.get("price", 0)), 8),
        )

    event_time = event.get("break_time")
    event_level = event.get("break_level")

    return (
        direction,
        event_time,
        (
            round(float(event_level), 8)
            if event_level is not None
            else None
        ),
    )


def find_recent_event(
    data,
    detector,
    lookback=80,
    minimum_bars=4,
):
    """
    使用指定 detector 往回掃描最近一次事件。

    detector 必須是可呼叫函式，例如：

    detect_bos_at_latest_bar
    detect_choch_at_latest_bar
    detect_liquidity_at_latest_bar

    detector 接收歷史 DataFrame，
    並回傳事件 dict 或 None。

    此函式負責：

    1. 往回掃描事件
    2. 避免同一結構點重複計算
    3. 計算 bars_ago
    4. 回傳最近一次有效事件
    """
    if len(data) < minimum_bars:
        return None

    start_index = max(
        minimum_bars - 1,
        len(data) - lookback,
    )

    used_event_keys = set()
    events = []

    for end_index in range(start_index, len(data)):
        history = data.iloc[: end_index + 1].copy()
        event = detector(history)

        if event is None:
            continue

        event_key = build_structure_key(event)

        if event_key in used_event_keys:
            continue

        used_event_keys.add(event_key)

        event = event.copy()
        event["bars_ago"] = len(data) - 1 - end_index
        events.append(event)

    return events[-1] if events else None


def format_recent_event(
    event,
    empty_text="無資料",
):
    """
    將最近事件格式化成方便終端機顯示的文字。

    預期事件欄位：
    - status
    - break_time
    - break_level
    - break_close
    - bars_ago
    """
    if event is None:
        return empty_text

    status = event.get("status", "未知事件")
    break_time = event.get("break_time")
    break_level = event.get("break_level")
    break_close = event.get("break_close")
    bars_ago = event.get("bars_ago")

    if break_time is not None:
        time_text = break_time.strftime("%m/%d %H:%M")
    else:
        time_text = "未知"

    if break_level is not None:
        level_text = f"{break_level:,.2f}"
    else:
        level_text = "未知"

    if break_close is not None:
        close_text = f"{break_close:,.2f}"
    else:
        close_text = "未知"

    if bars_ago is not None:
        bars_text = f"{bars_ago} 根 K 棒"
    else:
        bars_text = "未知"

    return (
        f"{status}｜"
        f"時間 {time_text}｜"
        f"突破價位 {level_text}｜"
        f"突破收盤 {close_text}｜"
        f"距今 {bars_text}"
    )


def copy_event_to_details(details, event):
    """
    將事件的共用欄位寫入 details。

    可以減少 BOS、CHOCH、Liquidity 等模組
    重複撰寫相同的欄位指定程式。
    """
    if event is None:
        return details

    details["break_level"] = event.get("break_level")
    details["break_close"] = event.get("break_close")
    details["break_time"] = event.get("break_time")
    details["bars_ago"] = event.get("bars_ago")
    details["direction"] = event.get("direction")

    return details