from data.kline_data import get_candles
from data.indicators import add_indicators

from analysis.swing import find_swings
from analysis.bos import detect_bos_at_latest_bar
from analysis.choch import detect_choch_at_latest_bar
from analysis.event_utils import (
    make_event_item,
    find_recent_event,
    format_recent_event,
    copy_event_to_details,
)


def make_liquidity_item(
    score,
    status,
    reason,
    risk=0,
    details=None,
):
    """
    建立 Liquidity Sweep 統一分析結果。
    """
    return make_event_item(
        name="Liquidity Sweep",
        category="流動性掃蕩",
        score=score,
        status=status,
        reason=reason,
        risk=risk,
        details=details,
    )


def find_last_swing(swings, side):
    """
    尋找最近一個指定方向的 Swing。

    side：
    - high
    - low
    """
    matches = [
        swing
        for swing in swings
        if swing.get("side") == side
    ]

    return matches[-1] if matches else None


def build_liquidity_snapshot(data):
    """
    使用最新 K 棒以前的資料建立流動性參考點。

    最新 K 棒不參與 Swing 計算，
    避免把尚未確認的 Pivot 當成正式結構點。
    """
    if len(data) < 2:
        return {
            "swings": [],
            "last_swing_high": None,
            "last_swing_low": None,
        }

    history = data.iloc[:-1].copy()
    swings = find_swings(history)

    return {
        "swings": swings,
        "last_swing_high": find_last_swing(swings, "high"),
        "last_swing_low": find_last_swing(swings, "low"),
    }


def get_volume_column(data):
    """
    自動尋找成交量欄位。

    支援常見名稱：
    - volume
    - vol
    """
    for column in ("volume", "vol"):
        if column in data.columns:
            return column

    return None


def calculate_volume_ratio(data, period=20):
    """
    計算最新成交量相對於前 period 根平均成交量的倍數。

    例如：
    1.50 代表最新成交量為平均量的 1.5 倍。
    """
    volume_column = get_volume_column(data)

    if volume_column is None or len(data) < 2:
        return None

    current_volume = float(data.iloc[-1][volume_column])

    history = data.iloc[:-1].tail(period)
    average_volume = history[volume_column].mean()

    if average_volume is None or average_volume <= 0:
        return None

    return current_volume / average_volume


def calculate_candle_quality(current, direction):
    """
    計算掃流動性 K 棒的拒絕品質。

    Sweep High：
    主要觀察上影線。

    Sweep Low：
    主要觀察下影線。
    """
    open_price = float(current["open"])
    high_price = float(current["high"])
    low_price = float(current["low"])
    close_price = float(current["close"])

    candle_range = high_price - low_price

    if candle_range <= 0:
        return {
            "candle_range": 0,
            "wick_size": 0,
            "wick_ratio": 0,
            "body_size": 0,
            "body_ratio": 0,
            "rejection_strength": "無效",
        }

    body_high = max(open_price, close_price)
    body_low = min(open_price, close_price)

    upper_wick = high_price - body_high
    lower_wick = body_low - low_price
    body_size = abs(close_price - open_price)

    if direction == "down":
        wick_size = upper_wick
    else:
        wick_size = lower_wick

    wick_ratio = wick_size / candle_range
    body_ratio = body_size / candle_range

    if wick_ratio >= 0.60:
        rejection_strength = "強"
    elif wick_ratio >= 0.40:
        rejection_strength = "中"
    elif wick_ratio >= 0.25:
        rejection_strength = "弱"
    else:
        rejection_strength = "不足"

    return {
        "candle_range": candle_range,
        "wick_size": wick_size,
        "wick_ratio": wick_ratio,
        "body_size": body_size,
        "body_ratio": body_ratio,
        "rejection_strength": rejection_strength,
    }


def detect_liquidity_at_latest_bar(data):
    """
    判斷最新一根 K 棒是否發生 Liquidity Sweep。

    Sweep High：
    1. 最高價刺破最近 Swing High
    2. 收盤重新回到 Swing High 下方
    3. 視為掃上方流動性，方向偏空

    Sweep Low：
    1. 最低價刺破最近 Swing Low
    2. 收盤重新站回 Swing Low 上方
    3. 視為掃下方流動性，方向偏多

    注意：
    Liquidity Sweep 使用影線刺破，
    BOS／CHOCH 使用收盤價確認。
    """
    if len(data) < 6:
        return None

    snapshot = build_liquidity_snapshot(data)
    current = data.iloc[-1]

    current_high = float(current["high"])
    current_low = float(current["low"])
    current_close = float(current["close"])
    current_time = current["timestamp"]

    last_swing_high = snapshot["last_swing_high"]
    last_swing_low = snapshot["last_swing_low"]

    sweep_high_event = None
    sweep_low_event = None

    if last_swing_high is not None:
        high_level = float(last_swing_high["price"])

        if current_high > high_level and current_close < high_level:
            penetration = current_high - high_level
            penetration_percent = (
                penetration / high_level * 100
                if high_level != 0
                else 0
            )

            candle_quality = calculate_candle_quality(
                current=current,
                direction="down",
            )

            sweep_high_event = {
                "event_type": "Liquidity Sweep",
                "direction": "down",
                "status": "Sweep High",
                "score": -1,
                "break_level": high_level,
                "break_close": current_close,
                "break_time": current_time,
                "break_index": len(data) - 1,
                "wick_price": current_high,
                "penetration": penetration,
                "penetration_percent": penetration_percent,
                "structure_point": last_swing_high,
                "candle_quality": candle_quality,
            }

    if last_swing_low is not None:
        low_level = float(last_swing_low["price"])

        if current_low < low_level and current_close > low_level:
            penetration = low_level - current_low
            penetration_percent = (
                penetration / low_level * 100
                if low_level != 0
                else 0
            )

            candle_quality = calculate_candle_quality(
                current=current,
                direction="up",
            )

            sweep_low_event = {
                "event_type": "Liquidity Sweep",
                "direction": "up",
                "status": "Sweep Low",
                "score": 1,
                "break_level": low_level,
                "break_close": current_close,
                "break_time": current_time,
                "break_index": len(data) - 1,
                "wick_price": current_low,
                "penetration": penetration,
                "penetration_percent": penetration_percent,
                "structure_point": last_swing_low,
                "candle_quality": candle_quality,
            }

    if sweep_high_event and sweep_low_event:
        high_strength = (
            sweep_high_event["penetration_percent"]
            + sweep_high_event["candle_quality"]["wick_ratio"]
        )

        low_strength = (
            sweep_low_event["penetration_percent"]
            + sweep_low_event["candle_quality"]["wick_ratio"]
        )

        if high_strength >= low_strength:
            return sweep_high_event

        return sweep_low_event

    if sweep_high_event is not None:
        return sweep_high_event

    if sweep_low_event is not None:
        return sweep_low_event

    return None


def find_recent_liquidity_event(data, lookback=80):
    """
    往回搜尋最近一次 Liquidity Sweep。

    事件掃描、去重與 bars_ago，
    統一交由 Event Framework 處理。
    """
    return find_recent_event(
        data=data,
        detector=detect_liquidity_at_latest_bar,
        lookback=lookback,
        minimum_bars=6,
    )


def find_structure_confirmation(
    data,
    liquidity_event,
    confirmation_bars=4,
):
    """
    檢查 Sweep 發生後，是否出現同方向 CHOCH 或 BOS。

    Sweep High：
    尋找 CHOCH Down 或 BOS Down。

    Sweep Low：
    尋找 CHOCH Up 或 BOS Up。

    最多檢查事件發生後 confirmation_bars 根 K 棒。
    """
    if liquidity_event is None:
        return {
            "choch_confirmed": False,
            "bos_confirmed": False,
            "choch_event": None,
            "bos_event": None,
            "confirmation_bars": confirmation_bars,
        }

    event_index = liquidity_event.get("break_index")

    if event_index is None:
        return {
            "choch_confirmed": False,
            "bos_confirmed": False,
            "choch_event": None,
            "bos_event": None,
            "confirmation_bars": confirmation_bars,
        }

    expected_direction = liquidity_event["direction"]

    choch_event = None
    bos_event = None

    final_index = min(
        len(data) - 1,
        event_index + confirmation_bars,
    )

    for end_index in range(event_index, final_index + 1):
        history = data.iloc[: end_index + 1].copy()

        detected_choch = detect_choch_at_latest_bar(history)

        if (
            detected_choch is not None
            and detected_choch.get("direction") == expected_direction
        ):
            detected_choch = detected_choch.copy()
            detected_choch["bars_after_sweep"] = (
                end_index - event_index
            )

            if choch_event is None:
                choch_event = detected_choch

        detected_bos = detect_bos_at_latest_bar(history)

        if (
            detected_bos is not None
            and detected_bos.get("direction") == expected_direction
        ):
            detected_bos = detected_bos.copy()
            detected_bos["bars_after_sweep"] = (
                end_index - event_index
            )

            if bos_event is None:
                bos_event = detected_bos

    return {
        "choch_confirmed": choch_event is not None,
        "bos_confirmed": bos_event is not None,
        "choch_event": choch_event,
        "bos_event": bos_event,
        "confirmation_bars": confirmation_bars,
    }


def evaluate_liquidity_quality(
    event,
    volume_ratio,
    confirmation,
):
    """
    評估 Liquidity Sweep 品質。

    品質來源：

    1. 影線拒絕
    2. 刺破幅度
    3. 成交量放大
    4. CHOCH 確認
    5. BOS 確認

    最終方向分數限制在 ±3，
    避免與 Pipeline 中獨立的 BOS／CHOCH 重複加權過度。
    """
    if event is None:
        return {
            "quality_points": 0,
            "quality_level": "無事件",
            "score": 0,
            "quality_reasons": [],
        }

    quality_points = 0
    quality_reasons = []

    candle_quality = event.get("candle_quality", {})
    wick_ratio = candle_quality.get("wick_ratio", 0)
    penetration_percent = event.get("penetration_percent", 0)

    if wick_ratio >= 0.60:
        quality_points += 2
        quality_reasons.append("影線拒絕強")
    elif wick_ratio >= 0.40:
        quality_points += 1
        quality_reasons.append("影線拒絕中等")
    else:
        quality_reasons.append("影線拒絕偏弱")

    if penetration_percent >= 0.05:
        quality_points += 1
        quality_reasons.append("刺破幅度明顯")
    elif penetration_percent >= 0.01:
        quality_reasons.append("刺破幅度有效")
    else:
        quality_reasons.append("刺破幅度很小")

    if volume_ratio is not None:
        if volume_ratio >= 1.50:
            quality_points += 2
            quality_reasons.append("成交量明顯放大")
        elif volume_ratio >= 1.20:
            quality_points += 1
            quality_reasons.append("成交量溫和放大")
        else:
            quality_reasons.append("成交量未明顯放大")
    else:
        quality_reasons.append("缺少成交量資料")

    if confirmation.get("choch_confirmed"):
        quality_points += 2
        quality_reasons.append("已有 CHOCH 確認")

    if confirmation.get("bos_confirmed"):
        quality_points += 2
        quality_reasons.append("已有 BOS 確認")

    if quality_points >= 6:
        quality_level = "強"
        absolute_score = 3
    elif quality_points >= 3:
        quality_level = "中"
        absolute_score = 2
    else:
        quality_level = "弱"
        absolute_score = 1

    direction = event.get("direction")
    score = (
        absolute_score
        if direction == "up"
        else -absolute_score
    )

    return {
        "quality_points": quality_points,
        "quality_level": quality_level,
        "score": score,
        "quality_reasons": quality_reasons,
    }


def apply_time_decay(score, bars_ago):
    """
    Liquidity Sweep 屬於短線訊號。

    0 根前：
    保留完整分數。

    1～2 根前：
    最多保留 ±2。

    3～4 根前：
    最多保留 ±1。

    超過 4 根：
    分數歸零。
    """
    if bars_ago is None:
        return 0

    direction = 1 if score >= 0 else -1
    absolute_score = abs(score)

    if bars_ago == 0:
        decayed_score = absolute_score
    elif bars_ago <= 2:
        decayed_score = min(absolute_score, 2)
    elif bars_ago <= 4:
        decayed_score = min(absolute_score, 1)
    else:
        decayed_score = 0

    return direction * decayed_score


def analyze_liquidity(
    data,
    lookback=80,
    confirmation_bars=4,
):
    """
    Liquidity Sweep V2：

    1. 偵測 Swing High／Low 的影線掃蕩。
    2. 評估影線拒絕程度。
    3. 評估刺破幅度。
    4. 評估成交量是否放大。
    5. 尋找後續 CHOCH／BOS 確認。
    6. 根據事件品質與時間距離計算分數。
    """
    if len(data) < 6:
        return make_liquidity_item(
            score=0,
            status="資料不足",
            reason="目前 K 棒資料不足，無法可靠判斷流動性掃蕩。",
            risk=1,
            details={},
        )

    snapshot = build_liquidity_snapshot(data)
    current = data.iloc[-1]

    current_event = detect_liquidity_at_latest_bar(data)
    recent_event = find_recent_liquidity_event(
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

    volume_ratio = calculate_volume_ratio(data)

    confirmation = find_structure_confirmation(
        data=data,
        liquidity_event=selected_event,
        confirmation_bars=confirmation_bars,
    )

    quality = evaluate_liquidity_quality(
        event=selected_event,
        volume_ratio=volume_ratio,
        confirmation=confirmation,
    )

    final_score = apply_time_decay(
        score=quality["score"],
        bars_ago=(
            selected_event.get("bars_ago")
            if selected_event is not None
            else None
        ),
    )

    details = {
        "current_high": current["high"],
        "current_low": current["low"],
        "current_close": current["close"],
        "last_swing_high": snapshot["last_swing_high"],
        "last_swing_low": snapshot["last_swing_low"],
        "current_event": current_event,
        "recent_event": recent_event,
        "selected_event": selected_event,
        "direction": None,
        "break_level": None,
        "break_close": None,
        "break_time": None,
        "bars_ago": None,
        "wick_price": None,
        "penetration": None,
        "penetration_percent": None,
        "wick_ratio": None,
        "rejection_strength": None,
        "volume_ratio": volume_ratio,
        "confirmation": confirmation,
        "quality": quality,
    }

    if selected_event is not None:
        copy_event_to_details(details, selected_event)

        candle_quality = selected_event.get(
            "candle_quality",
            {},
        )

        details["wick_price"] = selected_event.get(
            "wick_price"
        )
        details["penetration"] = selected_event.get(
            "penetration"
        )
        details["penetration_percent"] = selected_event.get(
            "penetration_percent"
        )
        details["wick_ratio"] = candle_quality.get(
            "wick_ratio"
        )
        details["rejection_strength"] = candle_quality.get(
            "rejection_strength"
        )

        if selected_event["direction"] == "up":
            direction_text = "掃下方流動性"
            reaction_text = "偏多"
        else:
            direction_text = "掃上方流動性"
            reaction_text = "偏空"

        confirmation_texts = []

        if confirmation["choch_confirmed"]:
            confirmation_texts.append("CHOCH 已確認")

        if confirmation["bos_confirmed"]:
            confirmation_texts.append("BOS 已確認")

        if confirmation_texts:
            confirmation_text = "、".join(confirmation_texts)
        else:
            confirmation_text = "尚無結構確認"

        quality_reason = "、".join(
            quality["quality_reasons"]
        )

        if selected_event.get("bars_ago", 0) == 0:
            status = (
                f"{selected_event['status']}｜"
                f"{quality['quality_level']}品質"
            )
        else:
            status = (
                f"最近 {selected_event['status']}｜"
                f"{quality['quality_level']}品質"
            )

        reason = (
            f"最近一次為{direction_text}事件，發生於 "
            f"{selected_event['break_time'].strftime('%m/%d %H:%M')}；"
            f"流動性價位 {selected_event['break_level']:,.2f}，"
            f"影線極值 {selected_event['wick_price']:,.2f}，"
            f"收盤價 {selected_event['break_close']:,.2f}，"
            f"距今 {selected_event['bars_ago']} 根 K 棒。"
            f"事件品質為{quality['quality_level']}，"
            f"評估依據：{quality_reason}；"
            f"{confirmation_text}，目前屬於短線{reaction_text}訊號。"
        )

        risk = 2

        if (
            quality["quality_level"] == "強"
            and (
                confirmation["choch_confirmed"]
                or confirmation["bos_confirmed"]
            )
        ):
            risk = 1

        if selected_event["bars_ago"] > 4:
            risk = 1

        return make_liquidity_item(
            score=final_score,
            status=status,
            reason=reason,
            risk=risk,
            details=details,
        )

    last_swing_high = snapshot["last_swing_high"]
    last_swing_low = snapshot["last_swing_low"]

    high_text = (
        f"{last_swing_high['price']:,.2f}"
        if last_swing_high is not None
        else "無資料"
    )

    low_text = (
        f"{last_swing_low['price']:,.2f}"
        if last_swing_low is not None
        else "無資料"
    )

    return make_liquidity_item(
        score=0,
        status="尚無 Liquidity Sweep",
        reason=(
            f"最新 K 棒尚未形成有效流動性掃蕩；"
            f"最近 Swing High 為 {high_text}，"
            f"最近 Swing Low 為 {low_text}。"
        ),
        risk=0,
        details=details,
    )


def format_swing_point(point):
    if point is None:
        return "無資料"

    return (
        f"{point['side'].upper()}｜"
        f"{point['price']:,.2f}｜"
        f"{point['time'].strftime('%m/%d %H:%M')}"
    )


def format_liquidity_event(event):
    if event is None:
        return "無資料"

    base_text = format_recent_event(event)

    wick_price = event.get("wick_price")
    penetration_percent = event.get(
        "penetration_percent"
    )

    candle_quality = event.get(
        "candle_quality",
        {},
    )

    wick_ratio = candle_quality.get("wick_ratio")

    wick_text = (
        f"{wick_price:,.2f}"
        if wick_price is not None
        else "未知"
    )

    penetration_text = (
        f"{penetration_percent:.3f}%"
        if penetration_percent is not None
        else "未知"
    )

    wick_ratio_text = (
        f"{wick_ratio * 100:.1f}%"
        if wick_ratio is not None
        else "未知"
    )

    return (
        f"{base_text}｜"
        f"影線極值 {wick_text}｜"
        f"刺破幅度 {penetration_text}｜"
        f"拒絕影線占比 {wick_ratio_text}"
    )


def format_confirmation(confirmation):
    if not confirmation:
        return "無資料"

    texts = []

    choch_event = confirmation.get("choch_event")
    bos_event = confirmation.get("bos_event")

    if choch_event is not None:
        texts.append(
            f"{choch_event['status']}，"
            f"發生於 Sweep 後 "
            f"{choch_event['bars_after_sweep']} 根"
        )

    if bos_event is not None:
        texts.append(
            f"{bos_event['status']}，"
            f"發生於 Sweep 後 "
            f"{bos_event['bars_after_sweep']} 根"
        )

    if not texts:
        return "尚無 CHOCH／BOS 確認"

    return "｜".join(texts)


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

    result = analyze_liquidity(data)
    details = result["details"]

    quality = details.get("quality", {})
    confirmation = details.get("confirmation", {})

    volume_ratio = details.get("volume_ratio")

    volume_text = (
        f"{volume_ratio:.2f} 倍"
        if volume_ratio is not None
        else "無資料"
    )

    print("\n" + "=" * 72)
    print("BTC 永續合約｜15 分鐘 Liquidity Sweep 分析 V2")
    print("=" * 72)
    print(
        "最近 Swing High："
        f"{format_swing_point(details.get('last_swing_high'))}"
    )
    print(
        "最近 Swing Low ："
        f"{format_swing_point(details.get('last_swing_low'))}"
    )
    print(f"最新最高價：{details.get('current_high', 0):,.2f}")
    print(f"最新最低價：{details.get('current_low', 0):,.2f}")
    print(f"最新收盤價：{details.get('current_close', 0):,.2f}")
    print(
        "最近事件："
        f"{format_liquidity_event(details.get('recent_event'))}"
    )
    print(f"成交量倍數：{volume_text}")
    print(
        "結構確認："
        f"{format_confirmation(confirmation)}"
    )
    print(
        "事件品質："
        f"{quality.get('quality_level', '無事件')}｜"
        f"品質點數 {quality.get('quality_points', 0)}"
    )
    print("-" * 72)
    print(f"狀態：{result['status']}")
    print(f"分數：{result['score']:+d}")
    print(f"風險：{result['risk']}")
    print(f"原因：{result['reason']}")
    print("=" * 72)