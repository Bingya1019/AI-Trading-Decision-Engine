from data.kline_data import get_candles
from data.indicators import add_indicators
from analysis.swing import find_swings
from analysis.structure import classify_swings
from analysis.trend_state import analyze_trend_state
from analysis.event_utils import (
    make_event_item,
    find_last_label,
    calculate_recent_event_score,
    find_recent_event,
    format_recent_event,
    copy_event_to_details,
)


def make_bos_item(score, status, reason, risk=0, details=None):
    """
    建立 BOS 統一分析結果。
    """
    return make_event_item(
        name="BOS",
        category="市場結構突破",
        score=score,
        status=status,
        reason=reason,
        risk=risk,
        details=details,
    )


def build_structure_snapshot(data):
    """
    建立指定時間點的市場結構快照。

    回傳：
    - 趨勢狀態
    - 最近 HH
    - 最近 LL
    - 已分類 Swing
    """
    swings = find_swings(data)
    classified_swings = classify_swings(swings)
    trend_result = analyze_trend_state(data)

    return {
        "trend": trend_result["trend"],
        "classified_swings": classified_swings,
        "last_hh": find_last_label(classified_swings, "HH"),
        "last_ll": find_last_label(classified_swings, "LL"),
    }


def detect_bos_at_latest_bar(data):
    """
    判斷最新一根 K 棒是否剛發生 BOS。

    BOS Up：
    1. 趨勢為 bull
    2. 前一收盤尚未突破最近 HH
    3. 最新收盤由下往上突破最近 HH

    BOS Down：
    1. 趨勢為 bear
    2. 前一收盤尚未跌破最近 LL
    3. 最新收盤由上往下跌破最近 LL
    """
    if len(data) < 2:
        return None

    snapshot = build_structure_snapshot(data)

    previous = data.iloc[-2]
    current = data.iloc[-1]

    previous_close = previous["close"]
    current_close = current["close"]

    trend = snapshot["trend"]
    last_hh = snapshot["last_hh"]
    last_ll = snapshot["last_ll"]

    if trend == "bull" and last_hh is not None:
        hh_price = last_hh["price"]

        if previous_close <= hh_price < current_close:
            return {
                "event_type": "BOS",
                "direction": "up",
                "status": "BOS Up",
                "score": 3,
                "trend": trend,
                "break_level": hh_price,
                "break_close": current_close,
                "break_time": current["timestamp"],
                "break_index": len(data) - 1,
                "structure_point": last_hh,
            }

    if trend == "bear" and last_ll is not None:
        ll_price = last_ll["price"]

        if previous_close >= ll_price > current_close:
            return {
                "event_type": "BOS",
                "direction": "down",
                "status": "BOS Down",
                "score": -3,
                "trend": trend,
                "break_level": ll_price,
                "break_close": current_close,
                "break_time": current["timestamp"],
                "break_index": len(data) - 1,
                "structure_point": last_ll,
            }

    return None


def find_recent_bos_event(data, lookback=80):
    """
    往回搜尋最近一次 BOS。

    掃描、事件去重與 bars_ago，
    統一交由 event_utils.find_recent_event 處理。
    """
    return find_recent_event(
        data=data,
        detector=detect_bos_at_latest_bar,
        lookback=lookback,
        minimum_bars=4,
    )


def analyze_bos(data, lookback=80):
    """
    BOS V2：

    1. 判斷最新 K 棒是否正在發生 BOS。
    2. 若最新 K 棒沒有 BOS，追蹤最近一次 BOS。
    3. 最近事件採時間衰減評分。
    4. 同一結構價位只記錄一次突破。
    """
    if len(data) < 2:
        return make_bos_item(
            score=0,
            status="資料不足",
            reason="至少需要兩根 K 棒，才能判斷是否發生結構突破。",
            risk=1,
            details={},
        )

    snapshot = build_structure_snapshot(data)

    previous = data.iloc[-2]
    current = data.iloc[-1]

    previous_close = previous["close"]
    current_close = current["close"]

    current_event = detect_bos_at_latest_bar(data)
    recent_event = find_recent_bos_event(
        data=data,
        lookback=lookback,
    )

    details = {
        "trend": snapshot["trend"],
        "current_close": current_close,
        "previous_close": previous_close,
        "last_hh": snapshot["last_hh"],
        "last_ll": snapshot["last_ll"],
        "current_event": current_event,
        "recent_event": recent_event,
        "break_level": None,
        "break_close": None,
        "break_time": None,
        "bars_ago": None,
        "direction": None,
    }

    if current_event is not None:
        current_event = current_event.copy()
        current_event["bars_ago"] = 0

        details["current_event"] = current_event
        copy_event_to_details(details, current_event)

        if current_event["direction"] == "up":
            reason = (
                f"市場維持 Bull 結構，最新收盤價 "
                f"{current_event['break_close']:,.2f} 正式突破最近 HH "
                f"{current_event['break_level']:,.2f}，確認多頭結構延續。"
            )
        else:
            reason = (
                f"市場維持 Bear 結構，最新收盤價 "
                f"{current_event['break_close']:,.2f} 正式跌破最近 LL "
                f"{current_event['break_level']:,.2f}，確認空頭結構延續。"
            )

        return make_bos_item(
            score=current_event["score"],
            status=current_event["status"],
            reason=reason,
            risk=0,
            details=details,
        )

    if recent_event is not None:
        recent_score = calculate_recent_event_score(recent_event)
        copy_event_to_details(details, recent_event)

        direction_text = (
            "多頭結構突破"
            if recent_event["direction"] == "up"
            else "空頭結構突破"
        )

        return make_bos_item(
            score=recent_score,
            status=f"最近 {recent_event['status']}",
            reason=(
                f"最近一次為{direction_text}，發生於 "
                f"{recent_event['break_time'].strftime('%m/%d %H:%M')}；"
                f"突破價位 {recent_event['break_level']:,.2f}，"
                f"突破收盤 {recent_event['break_close']:,.2f}，"
                f"距今 {recent_event['bars_ago']} 根 K 棒。"
            ),
            risk=0,
            details=details,
        )

    trend = snapshot["trend"]
    last_hh = snapshot["last_hh"]
    last_ll = snapshot["last_ll"]

    if trend == "bull":
        if last_hh is None:
            reason = "目前為 Bull 結構，但尚未找到可供突破確認的 HH。"
        else:
            reason = (
                f"市場目前為 Bull，但最新收盤價 {current_close:,.2f} "
                f"尚未由下往上突破最近 HH {last_hh['price']:,.2f}。"
            )

        return make_bos_item(
            score=0,
            status="尚無多頭 BOS",
            reason=reason,
            risk=0,
            details=details,
        )

    if trend == "bear":
        if last_ll is None:
            reason = "目前為 Bear 結構，但尚未找到可供跌破確認的 LL。"
        else:
            reason = (
                f"市場目前為 Bear，但最新收盤價 {current_close:,.2f} "
                f"尚未由上往下跌破最近 LL {last_ll['price']:,.2f}。"
            )

        return make_bos_item(
            score=0,
            status="尚無空頭 BOS",
            reason=reason,
            risk=0,
            details=details,
        )

    return make_bos_item(
        score=0,
        status="不判斷 BOS",
        reason="目前趨勢狀態為 Range，區間突破暫不視為 BOS。",
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

    result = analyze_bos(data)
    details = result["details"]

    print("\n" + "=" * 72)
    print("BTC 永續合約｜15 分鐘 BOS 分析 V2｜Event Framework")
    print("=" * 72)
    print(f"目前趨勢：{details.get('trend', '未知')}")
    print(f"前一收盤：{details.get('previous_close', 0):,.2f}")
    print(f"最新收盤：{details.get('current_close', 0):,.2f}")
    print(f"最近 HH：{format_structure_point(details.get('last_hh'))}")
    print(f"最近 LL：{format_structure_point(details.get('last_ll'))}")
    print(
        "最近事件："
        f"{format_recent_event(details.get('recent_event'))}"
    )
    print("-" * 72)
    print(f"狀態：{result['status']}")
    print(f"分數：{result['score']:+d}")
    print(f"風險：{result['risk']}")
    print(f"原因：{result['reason']}")
    print("=" * 72)