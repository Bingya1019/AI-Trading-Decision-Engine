from data.kline_data import get_candles
from data.indicators import add_indicators


def make_structure_item(score, status, reason, risk=0, details=None):
    return {
        "name": "市場結構",
        "category": "市場結構",
        "score": score,
        "status": status,
        "reason": reason,
        "risk": risk,
        "details": details or {},
    }


def find_swing_points(data, left=2, right=2):
    swing_highs = []
    swing_lows = []

    for i in range(left, len(data) - right):
        current_high = data.iloc[i]["high"]
        current_low = data.iloc[i]["low"]

        left_highs = data.iloc[i - left:i]["high"]
        right_highs = data.iloc[i + 1:i + 1 + right]["high"]

        left_lows = data.iloc[i - left:i]["low"]
        right_lows = data.iloc[i + 1:i + 1 + right]["low"]

        if current_high > left_highs.max() and current_high > right_highs.max():
            swing_highs.append({
                "index": i,
                "time": data.iloc[i]["timestamp"],
                "price": current_high,
                "type": "high",
            })

        if current_low < left_lows.min() and current_low < right_lows.min():
            swing_lows.append({
                "index": i,
                "time": data.iloc[i]["timestamp"],
                "price": current_low,
                "type": "low",
            })

    return swing_highs, swing_lows


def classify_highs(swing_highs):
    classified = []

    for i, point in enumerate(swing_highs):
        if i == 0:
            label = "H"
            meaning = "第一個高點，尚無法比較"
            chinese = "初始高點"
        else:
            previous = swing_highs[i - 1]

            if point["price"] > previous["price"]:
                label = "HH"
                meaning = "Higher High，更高的高點"
                chinese = "高點創高"
            else:
                label = "LH"
                meaning = "Lower High，更低的高點"
                chinese = "高點降低"

        classified.append({
            **point,
            "label": label,
            "meaning": meaning,
            "chinese": chinese,
        })

    return classified


def classify_lows(swing_lows):
    classified = []

    for i, point in enumerate(swing_lows):
        if i == 0:
            label = "L"
            meaning = "第一個低點，尚無法比較"
            chinese = "初始低點"
        else:
            previous = swing_lows[i - 1]

            if point["price"] > previous["price"]:
                label = "HL"
                meaning = "Higher Low，更高的低點"
                chinese = "低點墊高"
            else:
                label = "LL"
                meaning = "Lower Low，更低的低點"
                chinese = "低點跌破"

        classified.append({
            **point,
            "label": label,
            "meaning": meaning,
            "chinese": chinese,
        })

    return classified


def get_current_structure(data, classified_highs, classified_lows):
    current = data.iloc[-1]
    current_price = current["close"]

    last_high = classified_highs[-1] if classified_highs else None
    last_low = classified_lows[-1] if classified_lows else None

    distance_to_high = None
    distance_to_low = None
    distance_to_high_percent = None
    distance_to_low_percent = None
    price_position = "未知"
    position_reason = "目前缺少足夠 Swing High / Swing Low，無法判斷價格位置。"

    if last_high:
        distance_to_high = current_price - last_high["price"]
        distance_to_high_percent = (distance_to_high / last_high["price"]) * 100

    if last_low:
        distance_to_low = current_price - last_low["price"]
        distance_to_low_percent = (distance_to_low / last_low["price"]) * 100

    if last_high and last_low:
        high_price = last_high["price"]
        low_price = last_low["price"]
        price_range = high_price - low_price

        if price_range > 0:
            position_ratio = (current_price - low_price) / price_range

            if position_ratio >= 0.7:
                price_position = "高區"
                position_reason = "目前價格位於最近有效高低點區間的高位，追多風險較高。"
            elif position_ratio <= 0.3:
                price_position = "低區"
                position_reason = "目前價格位於最近有效高低點區間的低位，追空風險較高。"
            else:
                price_position = "中區"
                position_reason = "目前價格位於最近有效高低點區間的中段，多空仍需等待確認。"
        else:
            price_position = "區間異常"
            position_reason = "最近有效高點低於或等於有效低點，暫時不判斷價格位置。"

    return {
        "current_price": current_price,
        "last_high": last_high,
        "last_low": last_low,
        "distance_to_high": distance_to_high,
        "distance_to_low": distance_to_low,
        "distance_to_high_percent": distance_to_high_percent,
        "distance_to_low_percent": distance_to_low_percent,
        "price_position": price_position,
        "position_reason": position_reason,
    }


def analyze_structure(data):
    swing_highs, swing_lows = find_swing_points(data)
    classified_highs = classify_highs(swing_highs)
    classified_lows = classify_lows(swing_lows)

    recent_highs = classified_highs[-3:]
    recent_lows = classified_lows[-3:]

    high_labels = [item["label"] for item in recent_highs]
    low_labels = [item["label"] for item in recent_lows]

    hh_count = high_labels.count("HH")
    lh_count = high_labels.count("LH")
    hl_count = low_labels.count("HL")
    ll_count = low_labels.count("LL")

    current_structure = get_current_structure(
        data=data,
        classified_highs=classified_highs,
        classified_lows=classified_lows,
    )

    details = {
        "recent_highs": recent_highs,
        "recent_lows": recent_lows,
        "high_labels": high_labels,
        "low_labels": low_labels,
        "hh_count": hh_count,
        "lh_count": lh_count,
        "hl_count": hl_count,
        "ll_count": ll_count,
        "current_structure": current_structure,
    }

    if hh_count >= 1 and hl_count >= 1 and lh_count == 0 and ll_count == 0:
        return make_structure_item(
            score=3,
            status="健康多頭結構",
            reason="近期出現 HH 與 HL，高點與低點同步墊高，市場結構偏多。",
            risk=0,
            details=details,
        )

    if lh_count >= 1 and ll_count >= 1 and hh_count == 0 and hl_count == 0:
        return make_structure_item(
            score=-3,
            status="健康空頭結構",
            reason="近期出現 LH 與 LL，高點與低點同步下移，市場結構偏空。",
            risk=0,
            details=details,
        )

    if hh_count >= 1 and ll_count >= 1:
        return make_structure_item(
            score=0,
            status="結構混亂",
            reason="近期同時出現 HH 與 LL，代表市場波動加大，多空結構尚未一致。",
            risk=2,
            details=details,
        )

    if lh_count >= 1 and hl_count >= 1:
        return make_structure_item(
            score=0,
            status="收斂盤整",
            reason="近期出現 LH 與 HL，代表高點降低、低點墊高，市場可能進入收斂盤整。",
            risk=1,
            details=details,
        )

    if hh_count >= 1:
        return make_structure_item(
            score=1,
            status="高點墊高",
            reason="近期出現 HH，代表買方有推高價格，但仍需觀察低點是否同步墊高。",
            risk=0,
            details=details,
        )

    if ll_count >= 1:
        return make_structure_item(
            score=-1,
            status="低點下破",
            reason="近期出現 LL，代表賣方有壓低價格，但仍需觀察高點是否同步下移。",
            risk=1,
            details=details,
        )

    return make_structure_item(
        score=0,
        status="結構不明",
        reason="目前 Swing High / Swing Low 尚未形成明確 HH、HL、LH、LL 結構。",
        risk=1,
        details=details,
    )


def format_optional_number(value, digits=2):
    if value is None:
        return "無資料"

    return f"{value:,.{digits}f}"


def print_swing_points(title, points):
    print(title)

    if not points:
        print("・目前沒有足夠資料")
        return

    for point in points:
        print(
            f"・{point['time'].strftime('%m/%d %H:%M')}｜"
            f"{point['label']}（{point['chinese']}）｜"
            f"{point['price']:,.2f}｜"
            f"{point['meaning']}"
        )


def print_current_structure(current_structure):
    current_price = current_structure["current_price"]
    last_high = current_structure["last_high"]
    last_low = current_structure["last_low"]

    print("目前結構位置：")
    print(f"・目前價格：{current_price:,.2f}")

    if last_high:
        print(
            f"・最近有效高點："
            f"{last_high['price']:,.2f}｜"
            f"{last_high['label']}（{last_high['chinese']}）｜"
            f"{last_high['time'].strftime('%m/%d %H:%M')}"
        )
        print(
            f"・距離高點："
            f"{format_optional_number(current_structure['distance_to_high'])}｜"
            f"{format_optional_number(current_structure['distance_to_high_percent'])}%"
        )
    else:
        print("・最近有效高點：無資料")

    if last_low:
        print(
            f"・最近有效低點："
            f"{last_low['price']:,.2f}｜"
            f"{last_low['label']}（{last_low['chinese']}）｜"
            f"{last_low['time'].strftime('%m/%d %H:%M')}"
        )
        print(
            f"・距離低點："
            f"{format_optional_number(current_structure['distance_to_low'])}｜"
            f"{format_optional_number(current_structure['distance_to_low_percent'])}%"
        )
    else:
        print("・最近有效低點：無資料")

    print(f"・價格位置：{current_structure['price_position']}")
    print(f"・位置解讀：{current_structure['position_reason']}")


if __name__ == "__main__":
    candles = get_candles(symbol="BTC-USDT-SWAP", bar="15m", limit=150)
    candles = candles[candles["confirm"] == "1"].copy()

    data = add_indicators(candles)
    result = analyze_structure(data)

    print("\n" + "=" * 72)
    print("BTC 永續合約｜15 分鐘市場結構分析 V1.5")
    print("=" * 72)
    print(f"分類：{result['category']}")
    print(f"項目：{result['name']}")
    print(f"狀態：{result['status']}")
    print(f"分數：{result['score']:+d}")
    print(f"風險：{result['risk']}")
    print(f"原因：{result['reason']}")
    print("-" * 72)

    print_current_structure(result["details"]["current_structure"])
    print("-" * 72)

    print_swing_points("近期高點結構：", result["details"]["recent_highs"])
    print("-" * 72)
    print_swing_points("近期低點結構：", result["details"]["recent_lows"])

    print("=" * 72)