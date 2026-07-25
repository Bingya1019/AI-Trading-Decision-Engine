from data.kline_data import get_candles
from data.indicators import add_indicators

from analysis.bos import detect_bos_at_latest_bar
from analysis.choch import detect_choch_at_latest_bar
from analysis.event_utils import (
    make_event_item,
    find_recent_event,
    copy_event_to_details,
)


def make_order_block_item(
    score,
    status,
    reason,
    risk=0,
    details=None,
):
    """
    建立 Order Block 統一分析結果。
    """
    return make_event_item(
        name="Order Block",
        category="機構訂單區塊",
        score=score,
        status=status,
        reason=reason,
        risk=risk,
        details=details,
    )


def detect_structure_event_at_latest_bar(data):
    """
    尋找最新一根 K 棒發生的結構事件。

    優先判斷 CHOCH，再判斷 BOS。

    原因：
    CHOCH 代表原趨勢遭到破壞，
    在 Order Block 建立時具有較高的反轉意義。
    """
    choch_event = detect_choch_at_latest_bar(data)

    if choch_event is not None:
        event = choch_event.copy()
        event["source_event_type"] = "CHOCH"
        return event

    bos_event = detect_bos_at_latest_bar(data)

    if bos_event is not None:
        event = bos_event.copy()
        event["source_event_type"] = "BOS"
        return event

    return None


def find_origin_candle(
    data,
    direction,
    event_index,
    search_bars=8,
):
    """
    尋找造成結構突破前的最後一根反方向 K 棒。

    Bullish Order Block：
    向上突破之前的最後一根空方 K 棒。

    Bearish Order Block：
    向下突破之前的最後一根多方 K 棒。
    """
    if event_index is None or event_index <= 0:
        return None

    start_index = max(0, event_index - search_bars)

    for index in range(event_index - 1, start_index - 1, -1):
        candle = data.iloc[index]

        open_price = float(candle["open"])
        close_price = float(candle["close"])

        is_bearish = close_price < open_price
        is_bullish = close_price > open_price

        if direction == "up" and is_bearish:
            return {
                "index": index,
                "time": candle["timestamp"],
                "open": open_price,
                "high": float(candle["high"]),
                "low": float(candle["low"]),
                "close": close_price,
                "side": "bearish",
            }

        if direction == "down" and is_bullish:
            return {
                "index": index,
                "time": candle["timestamp"],
                "open": open_price,
                "high": float(candle["high"]),
                "low": float(candle["low"]),
                "close": close_price,
                "side": "bullish",
            }

    return None


def build_order_block_zone(origin_candle, direction):
    """
    建立 Order Block 價格區間。

    V1 使用原始 K 棒完整高低區間：

    zone_high = K 棒最高價
    zone_low  = K 棒最低價

    後續版本可再加入：
    - Body Order Block
    - 50% Mean Threshold
    - Refined Order Block
    """
    if origin_candle is None:
        return None

    zone_high = float(origin_candle["high"])
    zone_low = float(origin_candle["low"])
    midpoint = (zone_high + zone_low) / 2

    return {
        "direction": direction,
        "zone_high": zone_high,
        "zone_low": zone_low,
        "midpoint": midpoint,
        "origin_candle": origin_candle,
    }


def detect_order_block_at_latest_bar(
    data,
    search_bars=8,
):
    """
    判斷最新一根 K 棒是否建立新的 Order Block。

    建立條件：

    1. 最新 K 棒發生 BOS 或 CHOCH。
    2. 在突破前找到最後一根反方向 K 棒。
    3. 該 K 棒完整高低區間成為 Order Block。
    """
    if len(data) < 10:
        return None

    structure_event = detect_structure_event_at_latest_bar(data)

    if structure_event is None:
        return None

    direction = structure_event["direction"]
    event_index = len(data) - 1

    origin_candle = find_origin_candle(
        data=data,
        direction=direction,
        event_index=event_index,
        search_bars=search_bars,
    )

    if origin_candle is None:
        return None

    zone = build_order_block_zone(
        origin_candle=origin_candle,
        direction=direction,
    )

    if zone is None:
        return None

    if direction == "up":
        status = "Bullish Order Block"
        score = 2
    else:
        status = "Bearish Order Block"
        score = -2

    return {
        "event_type": "Order Block",
        "direction": direction,
        "status": status,
        "score": score,
        "break_level": structure_event.get("break_level"),
        "break_close": structure_event.get("break_close"),
        "break_time": structure_event.get("break_time"),
        "break_index": event_index,
        "structure_point": structure_event.get("structure_point"),
        "source_event_type": structure_event.get(
            "source_event_type"
        ),
        "source_event_status": structure_event.get("status"),
        "zone_high": zone["zone_high"],
        "zone_low": zone["zone_low"],
        "midpoint": zone["midpoint"],
        "origin_candle": origin_candle,
        "origin_time": origin_candle["time"],
        "origin_index": origin_candle["index"],
    }


def find_recent_order_block_event(
    data,
    lookback=100,
    search_bars=8,
):
    """
    往回搜尋最近一次建立的 Order Block。

    Event Framework 負責：
    - 歷史掃描
    - 去除重複事件
    - 計算 bars_ago
    """
    def detector(history):
        return detect_order_block_at_latest_bar(
            data=history,
            search_bars=search_bars,
        )

    return find_recent_event(
        data=data,
        detector=detector,
        lookback=lookback,
        minimum_bars=10,
    )


def evaluate_order_block_state(data, event):
    """
    評估最近 Order Block 目前狀態。

    狀態包括：

    created：
    最新 K 棒剛建立。

    rejection：
    價格進入 OB 後，收盤重新離開區間。

    inside：
    最新收盤位於 OB 區間內。

    active：
    OB 尚有效，但目前沒有回踩。

    invalidated：
    收盤價已穿越 OB 失效邊界。
    """
    if event is None or len(data) == 0:
        return {
            "state": "none",
            "state_text": "無 Order Block",
            "is_touched": False,
            "is_invalidated": False,
        }

    current = data.iloc[-1]

    current_high = float(current["high"])
    current_low = float(current["low"])
    current_close = float(current["close"])

    zone_high = float(event["zone_high"])
    zone_low = float(event["zone_low"])
    direction = event["direction"]
    bars_ago = event.get("bars_ago", 0)

    if bars_ago == 0:
        return {
            "state": "created",
            "state_text": "剛建立",
            "is_touched": False,
            "is_invalidated": False,
        }

    overlaps_zone = (
        current_low <= zone_high
        and current_high >= zone_low
    )

    close_inside_zone = (
        zone_low <= current_close <= zone_high
    )

    if direction == "up":
        if current_close < zone_low:
            return {
                "state": "invalidated",
                "state_text": "Bullish OB 已失效",
                "is_touched": overlaps_zone,
                "is_invalidated": True,
            }

        if overlaps_zone and current_close > zone_high:
            return {
                "state": "rejection",
                "state_text": "Bullish OB 回踩拒絕",
                "is_touched": True,
                "is_invalidated": False,
            }

        if close_inside_zone:
            return {
                "state": "inside",
                "state_text": "價格位於 Bullish OB",
                "is_touched": True,
                "is_invalidated": False,
            }

    if direction == "down":
        if current_close > zone_high:
            return {
                "state": "invalidated",
                "state_text": "Bearish OB 已失效",
                "is_touched": overlaps_zone,
                "is_invalidated": True,
            }

        if overlaps_zone and current_close < zone_low:
            return {
                "state": "rejection",
                "state_text": "Bearish OB 回踩拒絕",
                "is_touched": True,
                "is_invalidated": False,
            }

        if close_inside_zone:
            return {
                "state": "inside",
                "state_text": "價格位於 Bearish OB",
                "is_touched": True,
                "is_invalidated": False,
            }

    return {
        "state": "active",
        "state_text": "Order Block 仍有效",
        "is_touched": overlaps_zone,
        "is_invalidated": False,
    }


def calculate_order_block_score(event, state):
    """
    Order Block V1 評分。

    新建立：
    ±2

    回踩拒絕：
    ±2

    價格位於區間：
    ±1

    尚有效但未回踩：
    8 根 K 棒內 ±1

    失效或超過有效時間：
    0
    """
    if event is None:
        return 0

    direction = event["direction"]
    state_name = state["state"]
    bars_ago = event.get("bars_ago", 0)

    if state_name == "invalidated":
        strength = 0
    elif state_name == "created":
        strength = 2
    elif state_name == "rejection":
        strength = 2
    elif state_name == "inside":
        strength = 1
    elif state_name == "active" and bars_ago <= 8:
        strength = 1
    else:
        strength = 0

    return strength if direction == "up" else -strength


def analyze_order_block(
    data,
    lookback=100,
    search_bars=8,
):
    """
    Order Block V1：

    1. 使用 BOS／CHOCH 找出結構突破。
    2. 尋找突破前最後一根反方向 K 棒。
    3. 建立 Order Block 完整高低區間。
    4. 搜尋最近一次 Order Block。
    5. 判斷目前為有效、回踩、拒絕或失效。
    """
    if len(data) < 10:
        return make_order_block_item(
            score=0,
            status="資料不足",
            reason="目前 K 棒資料不足，無法可靠判斷 Order Block。",
            risk=1,
            details={},
        )

    current_event = detect_order_block_at_latest_bar(
        data=data,
        search_bars=search_bars,
    )

    recent_event = find_recent_order_block_event(
        data=data,
        lookback=lookback,
        search_bars=search_bars,
    )

    selected_event = (
        current_event
        if current_event is not None
        else recent_event
    )

    if selected_event is not None:
        selected_event = selected_event.copy()

        if current_event is not None:
            selected_event["bars_ago"] = 0

    state = evaluate_order_block_state(
        data=data,
        event=selected_event,
    )

    score = calculate_order_block_score(
        event=selected_event,
        state=state,
    )

    current = data.iloc[-1]

    details = {
        "current_close": float(current["close"]),
        "current_high": float(current["high"]),
        "current_low": float(current["low"]),
        "current_event": current_event,
        "recent_event": recent_event,
        "selected_event": selected_event,
        "direction": None,
        "break_level": None,
        "break_close": None,
        "break_time": None,
        "bars_ago": None,
        "zone_high": None,
        "zone_low": None,
        "midpoint": None,
        "origin_time": None,
        "source_event_type": None,
        "source_event_status": None,
        "state": state,
    }

    if selected_event is None:
        return make_order_block_item(
            score=0,
            status="尚無 Order Block",
            reason=(
                "最近資料中尚未找到由 BOS 或 CHOCH 建立的"
                "有效 Order Block。"
            ),
            risk=0,
            details=details,
        )

    copy_event_to_details(details, selected_event)

    details["zone_high"] = selected_event["zone_high"]
    details["zone_low"] = selected_event["zone_low"]
    details["midpoint"] = selected_event["midpoint"]
    details["origin_time"] = selected_event["origin_time"]
    details["source_event_type"] = selected_event[
        "source_event_type"
    ]
    details["source_event_status"] = selected_event[
        "source_event_status"
    ]

    direction = selected_event["direction"]

    if direction == "up":
        direction_text = "多方"
        order_block_text = "Bullish Order Block"
    else:
        direction_text = "空方"
        order_block_text = "Bearish Order Block"

    status = (
        f"{order_block_text}｜"
        f"{state['state_text']}"
    )

    reason = (
        f"最近一次 {order_block_text} 由 "
        f"{selected_event['source_event_status']} 建立；"
        f"來源 K 棒時間 "
        f"{selected_event['origin_time'].strftime('%m/%d %H:%M')}，"
        f"區間為 {selected_event['zone_low']:,.2f}～"
        f"{selected_event['zone_high']:,.2f}，"
        f"中間價 {selected_event['midpoint']:,.2f}。"
        f"結構突破發生於 "
        f"{selected_event['break_time'].strftime('%m/%d %H:%M')}，"
        f"距今 {selected_event['bars_ago']} 根 K 棒；"
        f"目前狀態為「{state['state_text']}」，"
        f"屬於{direction_text}結構參考區。"
    )

    if state["state"] == "invalidated":
        risk = 2
    elif state["state"] == "inside":
        risk = 2
    elif state["state"] == "rejection":
        risk = 1
    else:
        risk = 1

    return make_order_block_item(
        score=score,
        status=status,
        reason=reason,
        risk=risk,
        details=details,
    )


def format_order_block_event(event):
    if event is None:
        return "無資料"

    return (
        f"{event['status']}｜"
        f"來源 {event['source_event_status']}｜"
        f"形成時間 {event['break_time'].strftime('%m/%d %H:%M')}｜"
        f"OB K 棒 {event['origin_time'].strftime('%m/%d %H:%M')}｜"
        f"區間 {event['zone_low']:,.2f}～"
        f"{event['zone_high']:,.2f}｜"
        f"中間價 {event['midpoint']:,.2f}｜"
        f"距今 {event.get('bars_ago', 0)} 根 K 棒"
    )


if __name__ == "__main__":
    candles = get_candles(
        symbol="BTC-USDT-SWAP",
        bar="15m",
        limit=150,
    )

    candles = candles[
        candles["confirm"] == "1"
    ].copy()

    data = add_indicators(candles)

    result = analyze_order_block(data)
    details = result["details"]
    state = details.get("state", {})

    print("\n" + "=" * 72)
    print("BTC 永續合約｜15 分鐘 Order Block 分析 V1")
    print("=" * 72)
    print(
        "最近事件："
        f"{format_order_block_event(details.get('recent_event'))}"
    )
    print(f"最新收盤：{details.get('current_close', 0):,.2f}")
    print(
        "OB 區間："
        f"{details.get('zone_low', 0):,.2f}～"
        f"{details.get('zone_high', 0):,.2f}"
    )
    print(f"OB 中間價：{details.get('midpoint', 0):,.2f}")
    print(
        "來源事件："
        f"{details.get('source_event_status', '無資料')}"
    )
    print(
        "目前狀態："
        f"{state.get('state_text', '無資料')}"
    )
    print("-" * 72)
    print(f"狀態：{result['status']}")
    print(f"分數：{result['score']:+d}")
    print(f"風險：{result['risk']}")
    print(f"原因：{result['reason']}")
    print("=" * 72)