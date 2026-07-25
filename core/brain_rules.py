def normalize_text(value):
    """
    將可能為 None 的內容轉成可搜尋的小寫文字。
    """
    if value is None:
        return ""

    return str(value).strip().lower()


def find_score_item(score_items, *keywords):
    """
    從 Pipeline 結果中，依 name、category、status 搜尋模組。

    keywords 任一符合就回傳該項目。
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
    從模組結果判斷方向。

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


def get_item_state(item):
    """
    取得事件模組狀態。
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
    判斷事件是否仍具有分析價值。
    """
    if item is None:
        return False

    status_text = " ".join(
        [
            normalize_text(item.get("status")),
            normalize_text(item.get("reason")),
            get_item_state(item),
        ]
    )

    invalid_words = [
        "invalidated",
        "失效",
        "無 fvg",
        "尚無 fair value gap",
        "無 order block",
        "尚無 order block",
        "無 bos",
        "無 choch",
        "無流動性",
        "資料不足",
    ]

    return not any(
        word in status_text
        for word in invalid_words
    )


def make_rule(
    rule_id,
    title,
    direction,
    weight,
    description,
    matched_items=None,
):
    """
    建立統一規則結果。
    """
    return {
        "rule_id": rule_id,
        "title": title,
        "direction": direction,
        "weight": weight,
        "description": description,
        "matched_items": matched_items or [],
    }


def evaluate_smc_rules(score_items):
    """
    V4.0 Smart Money 共振規則引擎。

    第一版規則：
    1. CHOCH + Order Block + FVG
    2. Liquidity Sweep + CHOCH
    3. BOS + 趨勢 + FVG
    4. Order Block + FVG
    5. 結構事件方向衝突
    """

    trend = find_score_item(
        score_items,
        "趨勢",
        "trend",
    )

    bos = find_score_item(
        score_items,
        "bos",
        "市場結構突破",
    )

    choch = find_score_item(
        score_items,
        "choch",
        "市場結構反轉",
    )

    liquidity = find_score_item(
        score_items,
        "liquidity",
        "流動性掃蕩",
        "流動性",
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

    trend_direction = get_item_direction(trend)
    bos_direction = get_item_direction(bos)
    choch_direction = get_item_direction(choch)
    liquidity_direction = get_item_direction(liquidity)
    ob_direction = get_item_direction(order_block)
    fvg_direction = get_item_direction(fvg)

    matched_rules = []
    warnings = []

    bullish_points = 0
    bearish_points = 0

    # ==================================================
    # Rule 001：
    # CHOCH + Order Block + FVG 三重共振
    # ==================================================

    if (
        is_valid_event(choch)
        and is_valid_event(order_block)
        and is_valid_event(fvg)
        and choch_direction == "bullish"
        and ob_direction == "bullish"
        and fvg_direction == "bullish"
    ):
        rule = make_rule(
            rule_id="SMC-001-L",
            title="多方 CHOCH＋OB＋FVG 三重共振",
            direction="bullish",
            weight=5,
            description=(
                "市場已出現向上 CHOCH，並同時存在多方 "
                "Order Block 與 Bullish FVG，多方反轉結構較完整。"
            ),
            matched_items=[
                "CHOCH",
                "Order Block",
                "Fair Value Gap",
            ],
        )

        matched_rules.append(rule)
        bullish_points += rule["weight"]

    if (
        is_valid_event(choch)
        and is_valid_event(order_block)
        and is_valid_event(fvg)
        and choch_direction == "bearish"
        and ob_direction == "bearish"
        and fvg_direction == "bearish"
    ):
        rule = make_rule(
            rule_id="SMC-001-S",
            title="空方 CHOCH＋OB＋FVG 三重共振",
            direction="bearish",
            weight=5,
            description=(
                "市場已出現向下 CHOCH，並同時存在空方 "
                "Order Block 與 Bearish FVG，空方反轉結構較完整。"
            ),
            matched_items=[
                "CHOCH",
                "Order Block",
                "Fair Value Gap",
            ],
        )

        matched_rules.append(rule)
        bearish_points += rule["weight"]

    # ==================================================
    # Rule 002：
    # Liquidity Sweep + CHOCH
    # ==================================================

    if (
        is_valid_event(liquidity)
        and is_valid_event(choch)
        and liquidity_direction == "bullish"
        and choch_direction == "bullish"
    ):
        rule = make_rule(
            rule_id="SMC-002-L",
            title="掃低流動性後向上 CHOCH",
            direction="bullish",
            weight=4,
            description=(
                "價格掃過下方流動性後出現向上 CHOCH，"
                "符合潛在多方反轉流程。"
            ),
            matched_items=[
                "Liquidity Sweep",
                "CHOCH",
            ],
        )

        matched_rules.append(rule)
        bullish_points += rule["weight"]

    if (
        is_valid_event(liquidity)
        and is_valid_event(choch)
        and liquidity_direction == "bearish"
        and choch_direction == "bearish"
    ):
        rule = make_rule(
            rule_id="SMC-002-S",
            title="掃高流動性後向下 CHOCH",
            direction="bearish",
            weight=4,
            description=(
                "價格掃過上方流動性後出現向下 CHOCH，"
                "符合潛在空方反轉流程。"
            ),
            matched_items=[
                "Liquidity Sweep",
                "CHOCH",
            ],
        )

        matched_rules.append(rule)
        bearish_points += rule["weight"]

    # ==================================================
    # Rule 003：
    # BOS + 趨勢 + FVG
    # ==================================================

    if (
        is_valid_event(bos)
        and is_valid_event(fvg)
        and bos_direction == "bullish"
        and trend_direction == "bullish"
        and fvg_direction == "bullish"
    ):
        rule = make_rule(
            rule_id="SMC-003-L",
            title="多方趨勢延續共振",
            direction="bullish",
            weight=4,
            description=(
                "趨勢偏多、BOS 向上且存在 Bullish FVG，"
                "較符合多方延續結構。"
            ),
            matched_items=[
                "Trend",
                "BOS",
                "Fair Value Gap",
            ],
        )

        matched_rules.append(rule)
        bullish_points += rule["weight"]

    if (
        is_valid_event(bos)
        and is_valid_event(fvg)
        and bos_direction == "bearish"
        and trend_direction == "bearish"
        and fvg_direction == "bearish"
    ):
        rule = make_rule(
            rule_id="SMC-003-S",
            title="空方趨勢延續共振",
            direction="bearish",
            weight=4,
            description=(
                "趨勢偏空、BOS 向下且存在 Bearish FVG，"
                "較符合空方延續結構。"
            ),
            matched_items=[
                "Trend",
                "BOS",
                "Fair Value Gap",
            ],
        )

        matched_rules.append(rule)
        bearish_points += rule["weight"]

    # ==================================================
    # Rule 004：
    # Order Block + FVG 雙重區域共振
    # ==================================================

    if (
        is_valid_event(order_block)
        and is_valid_event(fvg)
        and ob_direction == "bullish"
        and fvg_direction == "bullish"
    ):
        rule = make_rule(
            rule_id="SMC-004-L",
            title="多方 OB＋FVG 區域共振",
            direction="bullish",
            weight=3,
            description=(
                "多方 Order Block 與 Bullish FVG 方向一致，"
                "價格回測相關區域時可能形成多方承接。"
            ),
            matched_items=[
                "Order Block",
                "Fair Value Gap",
            ],
        )

        matched_rules.append(rule)
        bullish_points += rule["weight"]

    if (
        is_valid_event(order_block)
        and is_valid_event(fvg)
        and ob_direction == "bearish"
        and fvg_direction == "bearish"
    ):
        rule = make_rule(
            rule_id="SMC-004-S",
            title="空方 OB＋FVG 區域共振",
            direction="bearish",
            weight=3,
            description=(
                "空方 Order Block 與 Bearish FVG 方向一致，"
                "價格反彈至相關區域時可能形成空方壓力。"
            ),
            matched_items=[
                "Order Block",
                "Fair Value Gap",
            ],
        )

        matched_rules.append(rule)
        bearish_points += rule["weight"]

    # ==================================================
    # Rule 005：
    # 結構衝突警告
    # ==================================================

    structure_directions = {
        direction
        for direction in [
            bos_direction,
            choch_direction,
            liquidity_direction,
            ob_direction,
            fvg_direction,
        ]
        if direction != "neutral"
    }

    if (
        "bullish" in structure_directions
        and "bearish" in structure_directions
    ):
        warnings.append(
            "SMC 事件方向並未完全一致，目前存在多空結構衝突。"
        )

    if (
        bos_direction != "neutral"
        and choch_direction != "neutral"
        and bos_direction != choch_direction
    ):
        warnings.append(
            "BOS 與 CHOCH 方向相反，可能處於趨勢轉折或震盪階段。"
        )

    if (
        ob_direction != "neutral"
        and fvg_direction != "neutral"
        and ob_direction != fvg_direction
    ):
        warnings.append(
            "Order Block 與 FVG 方向不一致，區域共振不足。"
        )

    net_points = bullish_points - bearish_points

    if net_points >= 6:
        smc_direction = "偏多"
    elif net_points <= -6:
        smc_direction = "偏空"
    else:
        smc_direction = "觀望"

    total_confluence = bullish_points + bearish_points

    if total_confluence >= 12:
        confluence_stars = "★★★★★"
    elif total_confluence >= 9:
        confluence_stars = "★★★★☆"
    elif total_confluence >= 6:
        confluence_stars = "★★★☆☆"
    elif total_confluence >= 3:
        confluence_stars = "★★☆☆☆"
    elif total_confluence >= 1:
        confluence_stars = "★☆☆☆☆"
    else:
        confluence_stars = "☆☆☆☆☆"

    bullish_rule_count = sum(
        rule["direction"] == "bullish"
        for rule in matched_rules
    )

    bearish_rule_count = sum(
        rule["direction"] == "bearish"
        for rule in matched_rules
    )

    if smc_direction == "偏多":
        action = (
            "多方 SMC 條件較完整，但不建議直接追多；"
            "等待價格回踩 Bullish Order Block 或 Bullish FVG，"
            "再配合低週期轉強確認。"
        )

    elif smc_direction == "偏空":
        action = (
            "空方 SMC 條件較完整，但不建議直接追空；"
            "等待價格反彈至 Bearish Order Block 或 Bearish FVG，"
            "再配合低週期轉弱確認。"
        )

    else:
        action = (
            "SMC 共振不足或多空訊號衝突，"
            "目前以觀望為主，等待新的 Sweep、CHOCH 或 BOS 確認。"
        )

    return {
        "direction": smc_direction,
        "bullish_points": bullish_points,
        "bearish_points": bearish_points,
        "net_points": net_points,
        "bullish_rule_count": bullish_rule_count,
        "bearish_rule_count": bearish_rule_count,
        "confluence_stars": confluence_stars,
        "matched_rules": matched_rules,
        "warnings": warnings,
        "action": action,
        "module_directions": {
            "trend": trend_direction,
            "bos": bos_direction,
            "choch": choch_direction,
            "liquidity": liquidity_direction,
            "order_block": ob_direction,
            "fvg": fvg_direction,
        },
    }