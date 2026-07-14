from data.kline_data import get_candles
from data.indicators import add_indicators
from analysis.swing import find_swings
from analysis.structure import classify_swings
from analysis.trend_state import analyze_trend_state


def make_bos_item(score, status, reason, risk=0, details=None):
    return {
        "name": "BOS",
        "category": "市場結構突破",
        "score": score,
        "status": status,
        "reason": reason,
        "risk": risk,
        "details": details or {},
    }


def find_last_label(classified_swings, label):
    """
    從已分類 Swing 中，尋找最近一個指定結構。
    例如：HH、LL。
    """
    matches = [
        item for item in classified_swings
        if item["label"] == label
    ]

    return matches[-1] if matches else None


def analyze_bos(data):
    """
    BOS V1 判斷規則：

    多頭 BOS：
    1. 趨勢狀態為 bull
    2. 前一根收盤價尚未突破最近 HH
    3. 最新收盤價正式突破最近 HH

    空頭 BOS：
    1. 趨勢狀態為 bear
    2. 前一根收盤價尚未跌破最近 LL
    3. 最新收盤價正式跌破最近 LL
    """
    if len(data) < 2:
        return make_bos_item(
            score=0,
            status="資料不足",
            reason="至少需要兩根 K 棒，才能判斷是否發生結構突破。",
            risk=1,
        )

    swings = find_swings(data)
    classified_swings = classify_swings(swings)
    trend_result = analyze_trend_state(data)

    current = data.iloc[-1]
    previous = data.iloc[-2]

    current_close = current["close"]
    previous_close = previous["close"]
    trend = trend_result["trend"]

    last_hh = find_last_label(classified_swings, "HH")
    last_ll = find_last_label(classified_swings, "LL")

    details = {
        "trend": trend,
        "current_close": current_close,
        "previous_close": previous_close,
        "last_hh": last_hh,
        "last_ll": last_ll,
        "break_level": None,
        "direction": None,
    }

    if trend == "bull":
        if last_hh is None:
            return make_bos_item(
                score=0,
                status="尚無多頭 BOS",
                reason="目前為多頭結構，但尚未找到可供突破確認的 HH。",
                details=details,
            )

        hh_price = last_hh["price"]

        if previous_close <= hh_price < current_close:
            details["break_level"] = hh_price
            details["direction"] = "up"

            return make_bos_item(
                score=3,
                status="BOS Up",
                reason=(
                    f"市場維持 Bull 結構，最新收盤價 {current_close:,.2f} "
                    f"正式突破最近 HH {hh_price:,.2f}，確認多頭結構延續。"
                ),
                risk=0,
                details=details,
            )

        return make_bos_item(
            score=0,
            status="尚無多頭 BOS",
            reason=(
                f"市場目前為 Bull，但最新收盤價 {current_close:,.2f} "
                f"尚未由下往上穿越最近 HH {hh_price:,.2f}。"
            ),
            details=details,
        )

    if trend == "bear":
        if last_ll is None:
            return make_bos_item(
                score=0,
                status="尚無空頭 BOS",
                reason="目前為空頭結構，但尚未找到可供跌破確認的 LL。",
                details=details,
            )

        ll_price = last_ll["price"]

        if previous_close >= ll_price > current_close:
            details["break_level"] = ll_price
            details["direction"] = "down"

            return make_bos_item(
                score=-3,
                status="BOS Down",
                reason=(
                    f"市場維持 Bear 結構，最新收盤價 {current_close:,.2f} "
                    f"正式跌破最近 LL {ll_price:,.2f}，確認空頭結構延續。"
                ),
                risk=0,
                details=details,
            )

        return make_bos_item(
            score=0,
            status="尚無空頭 BOS",
            reason=(
                f"市場目前為 Bear，但最新收盤價 {current_close:,.2f} "
                f"尚未由上往下穿越最近 LL {ll_price:,.2f}。"
            ),
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
    print("BTC 永續合約｜15 分鐘 BOS 分析 V1")
    print("=" * 72)
    print(f"目前趨勢：{details.get('trend', '未知')}")
    print(f"前一收盤：{details.get('previous_close', 0):,.2f}")
    print(f"最新收盤：{details.get('current_close', 0):,.2f}")
    print(f"最近 HH：{format_structure_point(details.get('last_hh'))}")
    print(f"最近 LL：{format_structure_point(details.get('last_ll'))}")
    print("-" * 72)
    print(f"狀態：{result['status']}")
    print(f"分數：{result['score']:+d}")
    print(f"風險：{result['risk']}")
    print(f"原因：{result['reason']}")
    print("=" * 72)