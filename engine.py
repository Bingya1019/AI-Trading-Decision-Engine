from data.kline_data import get_candles
from data.indicators import add_indicators


def score_to_stars(score):
    """
    將分數轉成星等。
    分數範圍約 -5 ~ +5
    """
    abs_score = abs(score)

    if abs_score >= 5:
        return "★★★★★"
    elif abs_score >= 4:
        return "★★★★☆"
    elif abs_score >= 3:
        return "★★★☆☆"
    elif abs_score >= 2:
        return "★★☆☆☆"
    elif abs_score >= 1:
        return "★☆☆☆☆"
    else:
        return "☆☆☆☆☆"


def analyze_market(symbol="BTC-USDT-SWAP", bar="15m", limit=200):
    """
    單一幣種、單一週期的交易分析核心。
    """

    candles = get_candles(symbol=symbol, bar=bar, limit=limit)
    candles = candles[candles["confirm"] == "1"].copy()

    data = add_indicators(candles)
    current = data.iloc[-1]
    previous = data.iloc[-2]

    price = current["close"]
    ema20 = current["ema20"]
    ema60 = current["ema60"]
    rsi = current["rsi14"]
    macd = current["macd"]
    macd_signal = current["macd_signal"]
    macd_hist = current["macd_hist"]
    prev_macd_hist = previous["macd_hist"]
    boll_high = current["boll_high"]
    boll_mid = current["boll_mid"]
    boll_low = current["boll_low"]

    score = 0
    reasons = []

    # 1. EMA 趨勢評分
    if ema20 > ema60 and price > ema20:
        score += 2
        trend = "偏多"
        reasons.append("價格站上 EMA20，且 EMA20 在 EMA60 上方，趨勢偏多")
    elif ema20 < ema60 and price < ema20:
        score -= 2
        trend = "偏空"
        reasons.append("價格跌破 EMA20，且 EMA20 在 EMA60 下方，趨勢偏空")
    elif ema20 > ema60:
        score += 1
        trend = "偏多"
        reasons.append("EMA20 在 EMA60 上方，但價格未完全站穩，趨勢偏多但不強")
    elif ema20 < ema60:
        score -= 1
        trend = "偏空"
        reasons.append("EMA20 在 EMA60 下方，但價格未完全跌破，趨勢偏空但不強")
    else:
        trend = "盤整"
        reasons.append("EMA20 與 EMA60 接近，趨勢不明顯")

    # 2. MACD 動能評分
    if macd_hist > 0 and macd_hist > prev_macd_hist:
        score += 2
        momentum = "偏多"
        reasons.append("MACD 柱體為正且放大，買方動能增強")
    elif macd_hist < 0 and macd_hist < prev_macd_hist:
        score -= 2
        momentum = "偏空"
        reasons.append("MACD 柱體為負且放大，賣方動能增強")
    elif macd_hist > 0:
        score += 1
        momentum = "偏多"
        reasons.append("MACD 柱體為正，但動能尚未明顯放大")
    elif macd_hist < 0:
        score -= 1
        momentum = "偏空"
        reasons.append("MACD 柱體為負，但動能尚未明顯放大")
    else:
        momentum = "中性"
        reasons.append("MACD 柱體接近 0，動能不明顯")

    # 3. RSI 風險修正
    if rsi >= 70:
        score -= 1
        rsi_status = "過熱"
        reasons.append(f"RSI {rsi:.2f}，進入偏高區，不宜追多")
    elif rsi <= 30:
        score += 1
        rsi_status = "過冷"
        reasons.append(f"RSI {rsi:.2f}，進入偏低區，不宜追空")
    elif rsi >= 55:
        score += 1
        rsi_status = "偏強"
        reasons.append(f"RSI {rsi:.2f}，位於偏強區")
    elif rsi <= 45:
        score -= 1
        rsi_status = "偏弱"
        reasons.append(f"RSI {rsi:.2f}，位於偏弱區")
    else:
        rsi_status = "中性"
        reasons.append(f"RSI {rsi:.2f}，位於中性區")

    # 4. 布林通道位置
    if price >= boll_high:
        score -= 1
        boll_status = "接近上軌"
        reasons.append("價格接近或突破布林上軌，追多風險提高")
    elif price <= boll_low:
        score += 1
        boll_status = "接近下軌"
        reasons.append("價格接近或跌破布林下軌，追空風險提高")
    elif price >= boll_mid:
        boll_status = "中軌上方"
        reasons.append("價格位於布林中軌上方")
    else:
        boll_status = "中軌下方"
        reasons.append("價格位於布林中軌下方")

    # 5. 最終方向
    if score >= 3:
        direction = "偏多"
        action = "條件偏多，可等待回踩或 5 分鐘轉強後觀察做多機會。"
    elif score <= -3:
        direction = "偏空"
        action = "條件偏空，可等待反彈或 5 分鐘轉弱後觀察做空機會。"
    else:
        direction = "觀望"
        action = "多空條件尚未明確一致，暫時不主動進場。"

    return {
        "symbol": symbol,
        "bar": bar,
        "time": current["timestamp"],
        "price": price,
        "ema20": ema20,
        "ema60": ema60,
        "rsi": rsi,
        "macd": macd,
        "macd_signal": macd_signal,
        "macd_hist": macd_hist,
        "boll_high": boll_high,
        "boll_mid": boll_mid,
        "boll_low": boll_low,
        "score": score,
        "stars": score_to_stars(score),
        "trend": trend,
        "momentum": momentum,
        "rsi_status": rsi_status,
        "boll_status": boll_status,
        "direction": direction,
        "action": action,
        "reasons": reasons,
    }


if __name__ == "__main__":
    result = analyze_market("BTC-USDT-SWAP", "15m")
    coin = result["symbol"].replace("-USDT-SWAP", "")

    print("\n" + "=" * 72)
    print(f"{coin} 永續合約｜{result['bar']} 交易引擎分析")
    print("=" * 72)
    print(f"判斷時間：{result['time'].strftime('%Y/%m/%d %H:%M')}")
    print(f"收盤價格：{result['price']:,.6f}")
    print(f"分析分數：{result['score']}｜強度：{result['stars']}")
    print(f"最終方向：{result['direction']}")
    print(f"短線趨勢：{result['trend']}｜市場動能：{result['momentum']}")
    print(f"RSI 狀態：{result['rsi_status']}（{result['rsi']:.2f}）")
    print(f"布林位置：{result['boll_status']}")
    print("-" * 72)
    print("判斷依據：")

    for reason in result["reasons"]:
        print(f"・{reason}")

    print("-" * 72)
    print(f"建議動作：{result['action']}")
    print("=" * 72)