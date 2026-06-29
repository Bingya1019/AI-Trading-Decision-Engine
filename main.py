from datetime import datetime

from data.market_data import symbols
from core.brain import analyze_brain
from core.report import generate_brain_report


def print_separator():
    print("=" * 72)


def print_coin_summary(symbol):
    result = analyze_brain(symbol=symbol, bar="15m")
    coin = symbol.replace("-USDT-SWAP", "")

    print(
        f"{coin:<5}｜"
        f"方向：{result['direction']:<4}｜"
        f"分數：{result['total_score']:+d}｜"
        f"強度：{result['strength']}｜"
        f"可信度：{result['confidence']}%｜"
        f"風險：{result['risk_stars']}｜"
        f"價格：{result['price']:,.4f}"
    )

    return result


if __name__ == "__main__":
    print("\n投資交易系統｜多幣種 15 分鐘 Brain 掃描")
    print(f"更新時間：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}")
    print_separator()

    results = []

    for symbol in symbols:
        try:
            result = print_coin_summary(symbol)
            results.append(result)
        except Exception as error:
            coin = symbol.replace("-USDT-SWAP", "")
            print(f"{coin:<5}｜分析失敗：{error}")

    print_separator()
    print("優先觀察清單")

    watch_list = [
        item for item in results
        if item["direction"] in ["偏多", "偏空"]
    ]

    if not watch_list:
        print("目前沒有明確偏多或偏空標的，整體以觀望為主。")
    else:
        for item in watch_list:
            coin = item["symbol"].replace("-USDT-SWAP", "")
            print(
                f"・{coin}：{item['direction']}｜"
                f"分數 {item['total_score']:+d}｜"
                f"可信度 {item['confidence']}%｜"
                f"{item['action']}"
            )

    print_separator()
    print("詳細分析：BTC")
    print(generate_brain_report("BTC-USDT-SWAP", "15m"))