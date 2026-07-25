def normalize_text(value):
    """
    將任意內容轉成方便比對的小寫文字。
    """
    if value is None:
        return ""

    return str(value).strip().lower()


def find_score_item(score_items, *keywords):
    """
    從 Pipeline 結果中搜尋指定模組。
    """
    normalized_keywords = [
        normalize_text(keyword)
        for keyword in keywords
    ]

    for item in score_items:
        searchable_text = " ".join(
            [
                normalize_text(item.get("name")),
                normalize_text(item.get("category")),
                normalize_text(item.get("status")),
                normalize_text(item.get("reason")),
            ]
        )

        if any(
            keyword in searchable_text
            for keyword in normalized_keywords
        ):
            return item

    return None


def get_item_direction(item):
    """
    判斷模組方向。

    回傳：
    bullish
    bearish
    neutral
    """
    if item is None:
        return "neutral"

    details = item.get("details") or {}

    detail_direction = normalize_text(
        details.get("direction")
    )

    if detail_direction in {
        "up",
        "bullish",
        "long",
        "多",
        "多方",
    }:
        return "bullish"

    if detail_direction in {
        "down",
        "bearish",
        "short",
        "空",
        "空方",
    }:
        return "bearish"

    text = " ".join(
        [
            normalize_text(item.get("status")),
            normalize_text(item.get("reason")),
        ]
    )

    bullish_words = [
        "bullish",
        "bos up",
        "choch up",
        "sweep low",
        "多方",
        "向上",
        "偏多",
        "做多",
    ]

    bearish_words = [
        "bearish",
        "bos down",
        "choch down",
        "sweep high",
        "空方",
        "向下",
        "偏空",
        "做空",
    ]

    bullish_match = any(
        word in text
        for word in bullish_words
    )

    bearish_match = any(
        word in text
        for word in bearish_words
    )

    if bullish_match and not bearish_match:
        return "bullish"

    if bearish_match and not bullish_match:
        return "bearish"

    score = item.get("score", 0)

    if score > 0:
        return "bullish"

    if score < 0:
        return "bearish"

    return "neutral"


def get_event_state(item):
    """
    取得事件狀態。
    """
    if item is None:
        return ""

    details = item.get("details") or {}
    state = details.get("state")

    if isinstance(state, dict):
        return normalize_text(
            state.get("state")
            or state.get("state_text")
        )

    return normalize_text(state)


def is_valid_event(item):
    """
    判斷事件是否有效。
    """
    if item is None:
        return False

    text = " ".join(
        [
            normalize_text(item.get("status")),
            normalize_text(item.get("reason")),
            get_event_state(item),
        ]
    )

    invalid_words = [
        "invalidated",
        "失效",
        "資料不足",
        "尚無 fair value gap",
        "無 fvg",
        "尚無 order block",
        "無 order block",
        "無 bos",
        "無 choch",
        "無流動性",
    ]

    return not any(
        word in text
        for word in invalid_words
    )


def get_zone(item):
    """
    從 Order Block 或 FVG 取得區域上下界。
    """
    if item is None:
        return None

    details = item.get("details") or {}

    low_keys = [
        "zone_low",
        "ob_low",
        "gap_low",
        "lower",
        "low",
    ]

    high_keys = [
        "zone_high",
        "ob_high",
        "gap_high",
        "upper",
        "high",
    ]

    zone_low = None
    zone_high = None

    for key in low_keys:
        value = details.get(key)

        if value is not None:
            zone_low = float(value)
            break

    for key in high_keys:
        value = details.get(key)

        if value is not None:
            zone_high = float(value)
            break

    if zone_low is None or zone_high is None:
        selected_event = (
            details.get("selected_event")
            or details.get("recent_event")
        )

        if isinstance(selected_event, dict):
            for key in low_keys:
                value = selected_event.get(key)

                if value is not None:
                    zone_low = float(value)
                    break

            for key in high_keys:
                value = selected_event.get(key)

                if value is not None:
                    zone_high = float(value)
                    break

    if zone_low is None or zone_high is None:
        return None

    return {
        "low": min(zone_low, zone_high),
        "high": max(zone_low, zone_high),
        "midpoint": (
            float(zone_low)
            + float(zone_high)
        ) / 2,
    }


def price_touches_zone(price, zone):
    """
    判斷目前價格是否位於區域內。
    """
    if zone is None:
        return False

    return (
        zone["low"]
        <= float(price)
        <= zone["high"]
    )


def make_step(
    step,
    name,
    completed,
    description,
):
    """
    建立流程步驟。
    """
    return {
        "step": step,
        "name": name,
        "completed": completed,
        "description": description,
    }


def build_bullish_state(
    price,
    liquidity,
    choch,
    order_block,
    fvg,
):
    """
    建立多方 SMC 流程。
    """
    liquidity_direction = get_item_direction(
        liquidity
    )

    choch_direction = get_item_direction(
        choch
    )

    ob_direction = get_item_direction(
        order_block
    )

    fvg_direction = get_item_direction(
        fvg
    )

    sweep_confirmed = (
        is_valid_event(liquidity)
        and liquidity_direction == "bullish"
    )

    choch_confirmed = (
        is_valid_event(choch)
        and choch_direction == "bullish"
    )

    ob_confirmed = (
        is_valid_event(order_block)
        and ob_direction == "bullish"
    )

    fvg_confirmed = (
        is_valid_event(fvg)
        and fvg_direction == "bullish"
    )

    ob_zone = get_zone(order_block)
    fvg_zone = get_zone(fvg)

    retrace_to_ob = (
        ob_confirmed
        and price_touches_zone(
            price,
            ob_zone,
        )
    )

    retrace_to_fvg = (
        fvg_confirmed
        and price_touches_zone(
            price,
            fvg_zone,
        )
    )

    retrace_confirmed = (
        retrace_to_ob
        or retrace_to_fvg
    )

    entry_ready = (
        sweep_confirmed
        and choch_confirmed
        and (
            ob_confirmed
            or fvg_confirmed
        )
        and retrace_confirmed
    )

    steps = [
        make_step(
            1,
            "Sweep Low",
            sweep_confirmed,
            (
                "已掃過下方流動性。"
                if sweep_confirmed
                else "等待 Sweep Low。"
            ),
        ),
        make_step(
            2,
            "CHOCH Up",
            choch_confirmed,
            (
                "已出現向上 CHOCH。"
                if choch_confirmed
                else "等待 CHOCH Up。"
            ),
        ),
        make_step(
            3,
            "Bullish Order Block",
            ob_confirmed,
            (
                "已找到有效多方 Order Block。"
                if ob_confirmed
                else "等待有效 Bullish Order Block。"
            ),
        ),
        make_step(
            4,
            "Bullish FVG",
            fvg_confirmed,
            (
                "已找到有效 Bullish FVG。"
                if fvg_confirmed
                else "等待有效 Bullish FVG。"
            ),
        ),
        make_step(
            5,
            "Retrace",
            retrace_confirmed,
            (
                "價格已回踩多方 OB 或 FVG 區域。"
                if retrace_confirmed
                else "等待價格回踩多方 OB 或 FVG。"
            ),
        ),
        make_step(
            6,
            "Entry Confirmation",
            entry_ready,
            (
                "多方結構與回踩條件已具備，"
                "仍需低週期轉強確認。"
                if entry_ready
                else "等待多方流程完整與低週期轉強。"
            ),
        ),
    ]

    completed_count = sum(
        step["completed"]
        for step in steps
    )

    return {
        "direction": "bullish",
        "direction_text": "多方",
        "completed_count": completed_count,
        "total_steps": len(steps),
        "progress": (
            completed_count
            / len(steps)
        ),
        "steps": steps,
        "entry_ready": entry_ready,
        "retrace_confirmed": retrace_confirmed,
        "zones": {
            "order_block": ob_zone,
            "fvg": fvg_zone,
        },
    }


def build_bearish_state(
    price,
    liquidity,
    choch,
    order_block,
    fvg,
):
    """
    建立空方 SMC 流程。
    """
    liquidity_direction = get_item_direction(
        liquidity
    )

    choch_direction = get_item_direction(
        choch
    )

    ob_direction = get_item_direction(
        order_block
    )

    fvg_direction = get_item_direction(
        fvg
    )

    sweep_confirmed = (
        is_valid_event(liquidity)
        and liquidity_direction == "bearish"
    )

    choch_confirmed = (
        is_valid_event(choch)
        and choch_direction == "bearish"
    )

    ob_confirmed = (
        is_valid_event(order_block)
        and ob_direction == "bearish"
    )

    fvg_confirmed = (
        is_valid_event(fvg)
        and fvg_direction == "bearish"
    )

    ob_zone = get_zone(order_block)
    fvg_zone = get_zone(fvg)

    retrace_to_ob = (
        ob_confirmed
        and price_touches_zone(
            price,
            ob_zone,
        )
    )

    retrace_to_fvg = (
        fvg_confirmed
        and price_touches_zone(
            price,
            fvg_zone,
        )
    )

    retrace_confirmed = (
        retrace_to_ob
        or retrace_to_fvg
    )

    entry_ready = (
        sweep_confirmed
        and choch_confirmed
        and (
            ob_confirmed
            or fvg_confirmed
        )
        and retrace_confirmed
    )

    steps = [
        make_step(
            1,
            "Sweep High",
            sweep_confirmed,
            (
                "已掃過上方流動性。"
                if sweep_confirmed
                else "等待 Sweep High。"
            ),
        ),
        make_step(
            2,
            "CHOCH Down",
            choch_confirmed,
            (
                "已出現向下 CHOCH。"
                if choch_confirmed
                else "等待 CHOCH Down。"
            ),
        ),
        make_step(
            3,
            "Bearish Order Block",
            ob_confirmed,
            (
                "已找到有效空方 Order Block。"
                if ob_confirmed
                else "等待有效 Bearish Order Block。"
            ),
        ),
        make_step(
            4,
            "Bearish FVG",
            fvg_confirmed,
            (
                "已找到有效 Bearish FVG。"
                if fvg_confirmed
                else "等待有效 Bearish FVG。"
            ),
        ),
        make_step(
            5,
            "Retrace",
            retrace_confirmed,
            (
                "價格已反彈至空方 OB 或 FVG 區域。"
                if retrace_confirmed
                else "等待價格反彈至空方 OB 或 FVG。"
            ),
        ),
        make_step(
            6,
            "Entry Confirmation",
            entry_ready,
            (
                "空方結構與回測條件已具備，"
                "仍需低週期轉弱確認。"
                if entry_ready
                else "等待空方流程完整與低週期轉弱。"
            ),
        ),
    ]

    completed_count = sum(
        step["completed"]
        for step in steps
    )

    return {
        "direction": "bearish",
        "direction_text": "空方",
        "completed_count": completed_count,
        "total_steps": len(steps),
        "progress": (
            completed_count
            / len(steps)
        ),
        "steps": steps,
        "entry_ready": entry_ready,
        "retrace_confirmed": retrace_confirmed,
        "zones": {
            "order_block": ob_zone,
            "fvg": fvg_zone,
        },
    }


def choose_primary_state(
    bullish_state,
    bearish_state,
):
    """
    選擇目前較完整的 SMC 流程。
    """
    bullish_count = bullish_state[
        "completed_count"
    ]

    bearish_count = bearish_state[
        "completed_count"
    ]

    if bullish_count > bearish_count:
        return bullish_state

    if bearish_count > bullish_count:
        return bearish_state

    if (
        bullish_state["entry_ready"]
        and not bearish_state["entry_ready"]
    ):
        return bullish_state

    if (
        bearish_state["entry_ready"]
        and not bullish_state["entry_ready"]
    ):
        return bearish_state

    return {
        "direction": "neutral",
        "direction_text": "觀望",
        "completed_count": bullish_count,
        "total_steps": bullish_state[
            "total_steps"
        ],
        "progress": bullish_state[
            "progress"
        ],
        "steps": [],
        "entry_ready": False,
        "retrace_confirmed": False,
        "zones": {
            "order_block": None,
            "fvg": None,
        },
    }


def build_state_action(primary_state):
    """
    根據主流程產生行動建議。
    """
    direction = primary_state[
        "direction"
    ]

    completed_count = primary_state[
        "completed_count"
    ]

    entry_ready = primary_state[
        "entry_ready"
    ]

    if direction == "bullish":
        if entry_ready:
            return (
                "多方流程已接近完成，"
                "等待 5 分鐘或更低週期出現轉強訊號後，"
                "再評估做多。"
            )

        if completed_count >= 4:
            return (
                "多方結構已成形，"
                "目前等待價格回踩 Bullish Order Block "
                "或 Bullish FVG。"
            )

        if completed_count >= 2:
            return (
                "多方流程正在建立，"
                "尚需有效 OB、FVG 或回踩確認。"
            )

        return (
            "多方流程尚不完整，暫不進場。"
        )

    if direction == "bearish":
        if entry_ready:
            return (
                "空方流程已接近完成，"
                "等待 5 分鐘或更低週期出現轉弱訊號後，"
                "再評估做空。"
            )

        if completed_count >= 4:
            return (
                "空方結構已成形，"
                "目前等待價格反彈至 Bearish Order Block "
                "或 Bearish FVG。"
            )

        if completed_count >= 2:
            return (
                "空方流程正在建立，"
                "尚需有效 OB、FVG 或回測確認。"
            )

        return (
            "空方流程尚不完整，暫不進場。"
        )

    return (
        "多空流程完成度相近，"
        "目前沒有明確主流程，先觀望。"
    )


def analyze_smc_state(
    score_items,
    price,
):
    """
    V4.1 SMC 流程狀態機。

    流程：
    1. Liquidity Sweep
    2. CHOCH
    3. Order Block
    4. FVG
    5. Retrace
    6. Entry Confirmation
    """
    liquidity = find_score_item(
        score_items,
        "liquidity",
        "流動性掃蕩",
        "流動性",
    )

    choch = find_score_item(
        score_items,
        "choch",
        "市場結構反轉",
    )

    order_block = find_score_item(
        score_items,
        "order block",
        "訂單塊",
    )

    fvg = find_score_item(
        score_items,
        "fair value gap",
        "fvg",
        "價格失衡",
    )

    bullish_state = build_bullish_state(
        price=price,
        liquidity=liquidity,
        choch=choch,
        order_block=order_block,
        fvg=fvg,
    )

    bearish_state = build_bearish_state(
        price=price,
        liquidity=liquidity,
        choch=choch,
        order_block=order_block,
        fvg=fvg,
    )

    primary_state = choose_primary_state(
        bullish_state=bullish_state,
        bearish_state=bearish_state,
    )

    action = build_state_action(
        primary_state
    )

    return {
        "primary": primary_state,
        "bullish": bullish_state,
        "bearish": bearish_state,
        "action": action,
    }