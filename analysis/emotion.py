def analyze_emotion(rsi):
    if rsi >= 70:
        return {
            "name": "RSI",
            "category": "情緒",
            "score": -1,
            "status": "過熱",
            "reason": f"RSI {rsi:.2f}，市場偏熱，不宜追多。",
            "risk": 2,
        }

    if rsi <= 30:
        return {
            "name": "RSI",
            "category": "情緒",
            "score": 1,
            "status": "過冷",
            "reason": f"RSI {rsi:.2f}，市場偏冷，不宜追空。",
            "risk": 2,
        }

    if rsi >= 55:
        return {
            "name": "RSI",
            "category": "情緒",
            "score": 1,
            "status": "偏強",
            "reason": f"RSI {rsi:.2f}，位於偏強區。",
            "risk": 0,
        }

    if rsi <= 45:
        return {
            "name": "RSI",
            "category": "情緒",
            "score": -1,
            "status": "偏弱",
            "reason": f"RSI {rsi:.2f}，位於偏弱區。",
            "risk": 0,
        }

    return {
        "name": "RSI",
        "category": "情緒",
        "score": 0,
        "status": "中性",
        "reason": f"RSI {rsi:.2f}，位於中性區。",
        "risk": 0,
    }