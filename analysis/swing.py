from data.kline_data import get_candles
from data.indicators import add_indicators


def find_pivots(data, left=2, right=2):
    """
    第一階段：找局部高低點。

    這裡找到的是 Pivot，不一定是最終有效 Swing。
    """
    pivots = []

    for i in range(left, len(data) - right):
        current_high = data.iloc[i]["high"]
        current_low = data.iloc[i]["low"]

        left_high = data.iloc[i - left:i]["high"]
        right_high = data.iloc[i + 1:i + 1 + right]["high"]

        left_low = data.iloc[i - left:i]["low"]
        right_low = data.iloc[i + 1:i + 1 + right]["low"]

        if current_high > left_high.max() and current_high > right_high.max():
            pivots.append({
                "side": "high",
                "price": current_high,
                "time": data.iloc[i]["timestamp"],
                "index": i,
            })

        if current_low < left_low.min() and current_low < right_low.min():
            pivots.append({
                "side": "low",
                "price": current_low,
                "time": data.iloc[i]["timestamp"],
                "index": i,
            })

    pivots.sort(key=lambda x: x["index"])
    return pivots


def choose_stronger_pivot(old_pivot, new_pivot):
    """
    連續出現同方向 Pivot 時，只保留更有效的那一個。

    HIGH：保留價格更高者。
    LOW ：保留價格更低者。
    """
    if old_pivot["side"] != new_pivot["side"]:
        return new_pivot

    if new_pivot["side"] == "high":
        return new_pivot if new_pivot["price"] > old_pivot["price"] else old_pivot

    if new_pivot["side"] == "low":
        return new_pivot if new_pivot["price"] < old_pivot["price"] else old_pivot

    return old_pivot


def filter_swings(pivots):
    """
    第二階段：把 Pivot 過濾成有效 Swing。

    目標：
    HIGH → LOW → HIGH → LOW
    或
    LOW → HIGH → LOW → HIGH

    如果連續出現 HIGH / HIGH，保留較高者。
    如果連續出現 LOW / LOW，保留較低者。
    """
    swings = []

    for pivot in pivots:
        if not swings:
            swings.append(pivot)
            continue

        last_swing = swings[-1]

        if pivot["side"] == last_swing["side"]:
            swings[-1] = choose_stronger_pivot(last_swing, pivot)
        else:
            swings.append(pivot)

    return swings


def find_swings(data, left=2, right=2):
    """
    對外使用的主函式。

    回傳已過濾的有效 Swing List。
    """
    pivots = find_pivots(data, left=left, right=right)
    swings = filter_swings(pivots)

    return swings


def print_swing_list(title, swings):
    print(title)

    if not swings:
        print("目前沒有足夠 Swing 資料")
        return

    for swing in swings:
        print(
            f"{swing['time'].strftime('%m/%d %H:%M')}｜"
            f"{swing['side'].upper()}｜"
            f"{swing['price']:,.2f}"
        )


if __name__ == "__main__":
    candles = get_candles(
        symbol="BTC-USDT-SWAP",
        bar="15m",
        limit=150,
    )

    candles = candles[candles["confirm"] == "1"].copy()
    data = add_indicators(candles)

    pivots = find_pivots(data)
    swings = filter_swings(pivots)

    print("\n" + "=" * 72)
    print("Swing Engine V2")
    print("=" * 72)
    print(f"原始 Pivot 數量：{len(pivots)}")
    print(f"有效 Swing 數量：{len(swings)}")
    print("-" * 72)

    print_swing_list("有效 Swing List：", swings)

    print("=" * 72)