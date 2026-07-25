from data.kline_data import get_candles
from data.indicators import add_indicators

from analysis.event_utils import (
    make_event_item,
    find_recent_event,
)


def make_fvg_item(
    score,
    status,
    reason,
    risk=0,
    details=None,
):
    """
    建立 Fair Value Gap 統一分析結果。
    """
    return make_event_item(
        name="Fair Value Gap",
        category="價格失衡",
        score=score,
        status=status,
        reason=reason,
        risk=risk,
        details=details or {},
    )


def detect_fvg_at_latest_bar(data):
    """
    偵測最新三根 K 棒是否形成 ICT Fair Value Gap。

    Bullish FVG：
    K3 low > K1 high

    Bearish FVG：
    K3 high < K1 low
    """
    if data is None or len(data) < 3:
        return None

    k1 = data.iloc[-3]
    k3 = data.iloc[-1]

    k1_high = float(k1["high"])
    k1_low = float(k1["low"])
    k3_high = float(k3["high"])
    k3_low = float(k3["low"])

    # Bullish FVG
    if k3_low > k1_high:
        gap_low = k1_high
        gap_high = k3_low
        gap_size = gap_high - gap_low
        midpoint = (gap_low + gap_high) / 2

        return {
            "event_type": "FVG",
            "direction": "up",
            "status": "Bullish FVG",
            "score": 2,
            "break_time": k3["timestamp"],
            "break_index": len(data) - 1,
            "gap_low": gap_low,
            "gap_high": gap_high,
            "gap_size": gap_size,
            "midpoint": midpoint,
        }

    # Bearish FVG
    if k3_high < k1_low:
        gap_low = k3_high
        gap_high = k1_low
        gap_size = gap_high - gap_low
        midpoint = (gap_low + gap_high) / 2

        return {
            "event_type": "FVG",
            "direction": "down",
            "status": "Bearish FVG",
            "score": -2,
            "break_time": k3["timestamp"],
            "break_index": len(data) - 1,
            "gap_low": gap_low,
            "gap_high": gap_high,
            "gap_size": gap_size,
            "midpoint": midpoint,
        }

    return None


def find_recent_fvg(
    data,
    lookback=100,
):
    """
    搜尋最近一次 Fair Value Gap。
    """
    return find_recent_event(
        data=data,
        detector=detect_fvg_at_latest_bar,
        lookback=lookback,
        minimum_bars=3,
    )


def evaluate_fvg_state(data, event):
    """
    判斷 FVG 狀態：

    created
    untouched
    partial_fill
    filled
    """
    if event is None:
        return {
            "state": "none",
            "state_text": "無 FVG",
        }

    bars_ago = int(event.get("bars_ago", 0))

    if bars_ago == 0:
        return {
            "state": "created",
            "state_text": "剛形成",
        }

    gap_low = float(event["gap_low"])
    gap_high = float(event["gap_high"])
    direction = event["direction"]

    event_index = event.get("break_index")

    if event_index is None:
        event_index = max(
            len(data) - bars_ago - 1,
            0,
        )

    following_data = data.iloc[
        int(event_index) + 1:
    ]

    if following_data.empty:
        return {
            "state": "created",
            "state_text": "剛形成",
        }

    # Bullish FVG：
    # 價格由上往下回補
    if direction == "up":
        lowest_low = float(
            following_data["low"].min()
        )

        if lowest_low > gap_high:
            return {
                "state": "untouched",
                "state_text": "尚未回補",
            }

        if lowest_low > gap_low:
            return {
                "state": "partial_fill",
                "state_text": "部分回補",
            }

        return {
            "state": "filled",
            "state_text": "完全回補",
        }

    # Bearish FVG：
    # 價格由下往上回補
    highest_high = float(
        following_data["high"].max()
    )

    if highest_high < gap_low:
        return {
            "state": "untouched",
            "state_text": "尚未回補",
        }

    if highest_high < gap_high:
        return {
            "state": "partial_fill",
            "state_text": "部分回補",
        }

    return {
        "state": "filled",
        "state_text": "完全回補",
    }


def calculate_fvg_score(event, state):
    """
    FVG V1 評分。
    """
    if event is None:
        return 0

    direction = event["direction"]
    bars_ago = int(event.get("bars_ago", 0))
    state_name = state.get("state", "none")

    if state_name == "filled":
        strength = 0
    elif bars_ago > 8:
        strength = 0
    elif state_name in {
        "created",
        "untouched",
    }:
        strength = 2
    elif state_name == "partial_fill":
        strength = 1
    else:
        strength = 0

    if direction == "up":
        return strength

    return -strength


def analyze_fvg(
    data,
    lookback=100,
):
    """
    Fair Value Gap V1 分析。

    流程：
    1. 偵測最新 K 棒是否形成 FVG。
    2. 搜尋最近一次 FVG。
    3. 判斷是否回補。
    4. 計算方向分數與風險。
    """
    if data is None or len(data) < 3:
        return make_fvg_item(
            score=0,
            status="資料不足",
            reason=(
                "至少需要 3 根 K 棒，"
                "才能判斷 Fair Value Gap。"
            ),
            risk=1,
            details={},
        )

    current_event = detect_fvg_at_latest_bar(
        data
    )

    recent_event = find_recent_fvg(
        data=data,
        lookback=lookback,
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
            selected_event[
                "break_index"
            ] = len(data) - 1

    state = evaluate_fvg_state(
        data=data,
        event=selected_event,
    )

    score = calculate_fvg_score(
        event=selected_event,
        state=state,
    )

    current = data.iloc[-1]

    details = {
        "current_high": float(
            current["high"]
        ),
        "current_low": float(
            current["low"]
        ),
        "current_close": float(
            current["close"]
        ),
        "current_event": current_event,
        "recent_event": recent_event,
        "selected_event": selected_event,
        "direction": None,
        "event_time": None,
        "bars_ago": None,
        "gap_low": None,
        "gap_high": None,
        "gap_size": None,
        "midpoint": None,
        "state": state,
    }

    if selected_event is None:
        return make_fvg_item(
            score=0,
            status="尚無 Fair Value Gap",
            reason=(
                "最近資料中尚未找到符合三根 K 棒"
                "失衡條件的 Bullish FVG 或 "
                "Bearish FVG。"
            ),
            risk=0,
            details=details,
        )

    direction = selected_event["direction"]
    bars_ago = int(
        selected_event.get("bars_ago", 0)
    )

    gap_low = float(
        selected_event["gap_low"]
    )
    gap_high = float(
        selected_event["gap_high"]
    )
    gap_size = float(
        selected_event["gap_size"]
    )
    midpoint = float(
        selected_event["midpoint"]
    )

    details.update(
        {
            "direction": direction,
            "event_time": selected_event[
                "break_time"
            ],
            "bars_ago": bars_ago,
            "gap_low": gap_low,
            "gap_high": gap_high,
            "gap_size": gap_size,
            "midpoint": midpoint,
        }
    )

    if direction == "up":
        fvg_text = "Bullish FVG"
        direction_text = "多方"
        zone_text = "潛在多方支撐區"
    else:
        fvg_text = "Bearish FVG"
        direction_text = "空方"
        zone_text = "潛在空方壓力區"

    if bars_ago == 0:
        status = (
            f"{fvg_text}｜"
            f"{state['state_text']}"
        )
    else:
        status = (
            f"最近 {fvg_text}｜"
            f"{state['state_text']}"
        )

    event_time = selected_event[
        "break_time"
    ]

    reason = (
        f"最近一次 {fvg_text} 形成於 "
        f"{event_time.strftime('%m/%d %H:%M')}；"
        f"缺口區間為 {gap_low:,.2f}～"
        f"{gap_high:,.2f}，"
        f"缺口大小 {gap_size:,.2f}，"
        f"中間價 {midpoint:,.2f}，"
        f"距今 {bars_ago} 根 K 棒。"
        f"目前狀態為「{state['state_text']}」，"
        f"可視為{direction_text}價格失衡形成的"
        f"{zone_text}。"
    )

    state_name = state["state"]

    if state_name == "created":
        risk = 2
    elif state_name == "untouched":
        risk = 1
    elif state_name == "partial_fill":
        risk = 2
    else:
        risk = 0

    return make_fvg_item(
        score=score,
        status=status,
        reason=reason,
        risk=risk,
        details=details,
    )


def format_fvg_event(event):
    """
    格式化 FVG 事件。
    """
    if event is None:
        return "無資料"

    break_time = event.get("break_time")
    bars_ago = int(
        event.get("bars_ago", 0)
    )

    if break_time is not None:
        time_text = break_time.strftime(
            "%m/%d %H:%M"
        )
    else:
        time_text = "未知"

    return (
        f"{event.get('status', '未知事件')}｜"
        f"形成時間 {time_text}｜"
        f"區間 {event['gap_low']:,.2f}～"
        f"{event['gap_high']:,.2f}｜"
        f"缺口大小 {event['gap_size']:,.2f}｜"
        f"中間價 {event['midpoint']:,.2f}｜"
        f"距今 {bars_ago} 根 K 棒"
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

    result = analyze_fvg(data)
    details = result.get("details", {})
    state = details.get("state", {})

    gap_low = details.get("gap_low")
    gap_high = details.get("gap_high")
    gap_size = details.get("gap_size")
    midpoint = details.get("midpoint")

    if (
        gap_low is not None
        and gap_high is not None
    ):
        gap_range_text = (
            f"{gap_low:,.2f}～"
            f"{gap_high:,.2f}"
        )
    else:
        gap_range_text = "無資料"

    if gap_size is not None:
        gap_size_text = (
            f"{gap_size:,.2f}"
        )
    else:
        gap_size_text = "無資料"

    if midpoint is not None:
        midpoint_text = (
            f"{midpoint:,.2f}"
        )
    else:
        midpoint_text = "無資料"

    print("\n" + "=" * 72)
    print(
        "BTC 永續合約｜"
        "15 分鐘 Fair Value Gap 分析 V1"
    )
    print("=" * 72)

    print(
        "最近事件："
        f"{format_fvg_event(details.get('recent_event'))}"
    )

    print(
        "最新最高價："
        f"{details.get('current_high', 0):,.2f}"
    )

    print(
        "最新最低價："
        f"{details.get('current_low', 0):,.2f}"
    )

    print(
        "最新收盤價："
        f"{details.get('current_close', 0):,.2f}"
    )

    print(
        f"FVG 區間：{gap_range_text}"
    )
    print(
        f"缺口大小：{gap_size_text}"
    )
    print(
        f"中間價：{midpoint_text}"
    )

    print(
        "目前狀態："
        f"{state.get('state_text', '無資料')}"
    )

    print("-" * 72)
    print(
        f"狀態：{result['status']}"
    )
    print(
        f"分數：{result['score']:+d}"
    )
    print(
        f"風險：{result['risk']}"
    )
    print(
        f"原因：{result['reason']}"
    )
    print("=" * 72)