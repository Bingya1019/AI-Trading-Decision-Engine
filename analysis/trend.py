def analyze_trend(price, ema20, ema60):
    if ema20 > ema60 and price > ema20:
        return {
            "name": "EMA",
            "category": "趨勢",
            "score": 2,
            "status": "偏多",
            "reason": "價格站上 EMA20，且 EMA20 在 EMA60 上方，趨勢偏多。",
            "risk": 0,
        }

    if ema20 < ema60 and price < ema20:
        return {
            "name": "EMA",
            "category": "趨勢",
            "score": -2,
            "status": "偏空",
            "reason": "價格跌破 EMA20，且 EMA20 在 EMA60 下方，趨勢偏空。",
            "risk": 0,
        }

    if ema20 > ema60:
        return {
            "name": "EMA",
            "category": "趨勢",
            "score": 1,
            "status": "偏多但不強",
            "reason": "EMA20 在 EMA60 上方，但價格尚未完全站穩 EMA20。",
            "risk": 0,
        }

    if ema20 < ema60:
        return {
            "name": "EMA",
            "category": "趨勢",
            "score": -1,
            "status": "偏空但不強",
            "reason": "EMA20 在 EMA60 下方，但價格尚未完全跌破 EMA20。",
            "risk": 0,
        }

    return {
        "name": "EMA",
        "category": "趨勢",
        "score": 0,
        "status": "盤整",
        "reason": "EMA20 與 EMA60 接近，趨勢不明顯。",
        "risk": 0,
    }