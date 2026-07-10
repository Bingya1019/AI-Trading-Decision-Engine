from data.kline_data import get_candles
from data.indicators import add_indicators
from analysis.swing import find_swings
from analysis.structure import classify_swings


def make_trend_state(status, trend, reason, details=None):
    return {
        "name": "Trend State",
        "category": "趨勢狀態",
        "status": status,
        "trend": trend,
        "reason": reason,
        "details": details or {},
    }


def analyze_trend_state(data):
    """
    依照最近已分類的 Swing 結構，判斷市場狀態：

    bull  = 多頭結構
    bear  = 空頭結構
    range = 盤整或結構不一致
    """
    swings = find_swings(data)
    classified_swings = classify_swings(swings)

    highs = [
        item for item in classified_swings
        if item["side"] == "high"
    ]

    lows = [
        item for item in classified_swings
        if item["side"] == "low"
    ]

    recent_highs = highs[-2:]
    recent_lows = lows[-2:]

    high_labels = [item["label"] for item in recent_highs]
    low_labels = [item["label"] for item in recent_lows]

    last_high = highs[-1] if highs else None
    last_low = lows[-1] if lows else None

    details = {
        "recent_highs": recent_highs,
        "recent_lows": recent_lows,
        "high_labels": high_labels,
        "low_labels": low_labels,
        "last_high": last_high,
        "last_low": last_low,
    }

    if "HH" in high_labels and "HL" in low_labels:
        return make_trend_state(
            status="Bull",
            trend="bull",
            reason="近期出現 HH 與 HL，高點及低點同步墊高，多頭結構成立。",
            details=details,
        )

    if "LH" in high_labels and "LL" in low_labels:
        return make_trend_state(
            status="Bear",
            trend="bear",
            reason="近期出現 LH 與 LL，高點及低點同步下移，空頭結構成立。",
            details=details,
        )

    return make_trend_state(
        status="Range",
        trend="range",
        reason="近期高低點結構未形成一致的 HH＋HL 或 LH＋LL，暫定為盤整或過渡狀態。",
        details=details,
    )


def format_point(point):
    if point is None:
        return "無資料"

    return (
        f"{point['label']}（{point['chinese']}）｜"
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

    result = analyze_trend_state(data)

    print("\n" + "=" * 72)
    print("BTC 永續合約｜15 分鐘趨勢狀態分析")
    print("=" * 72)
    print(f"目前趨勢：{result['status']}")
    print(f"內部代碼：{result['trend']}")
    print(f"判斷原因：{result['reason']}")
    print("-" * 72)
    print(f"最近有效高點：{format_point(result['details']['last_high'])}")
    print(f"最近有效低點：{format_point(result['details']['last_low'])}")
    print("=" * 72)