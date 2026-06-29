def analyze_momentum(macd_hist, previous_macd_hist):
    if macd_hist > 0 and macd_hist > previous_macd_hist:
        return {
            "name": "MACD",
            "category": "動能",
            "score": 2,
            "status": "買方動能增強",
            "reason": "MACD 柱體為正且放大，買方動能增強。",
            "risk": 0,
        }

    if macd_hist < 0 and macd_hist < previous_macd_hist:
        return {
            "name": "MACD",
            "category": "動能",
            "score": -2,
            "status": "賣方動能增強",
            "reason": "MACD 柱體為負且放大，賣方動能增強。",
            "risk": 0,
        }

    if macd_hist > 0:
        return {
            "name": "MACD",
            "category": "動能",
            "score": 1,
            "status": "買方動能偏強",
            "reason": "MACD 柱體為正，但尚未明顯放大。",
            "risk": 0,
        }

    if macd_hist < 0:
        return {
            "name": "MACD",
            "category": "動能",
            "score": -1,
            "status": "賣方動能偏強",
            "reason": "MACD 柱體為負，但尚未明顯放大。",
            "risk": 0,
        }

    return {
        "name": "MACD",
        "category": "動能",
        "score": 0,
        "status": "動能不明",
        "reason": "MACD 柱體接近 0，多空動能不明顯。",
        "risk": 0,
    }