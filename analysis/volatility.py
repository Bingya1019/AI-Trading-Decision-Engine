def analyze_volatility(price, boll_high, boll_mid, boll_low):
    if price >= boll_high:
        return {
            "name": "布林通道",
            "category": "波動",
            "score": -1,
            "status": "接近上軌",
            "reason": "價格接近或突破布林上軌，追多風險提高。",
            "risk": 2,
        }

    if price <= boll_low:
        return {
            "name": "布林通道",
            "category": "波動",
            "score": 1,
            "status": "接近下軌",
            "reason": "價格接近或跌破布林下軌，追空風險提高。",
            "risk": 2,
        }

    if price >= boll_mid:
        return {
            "name": "布林通道",
            "category": "波動",
            "score": 0,
            "status": "中軌上方",
            "reason": "價格位於布林中軌上方。",
            "risk": 0,
        }

    return {
        "name": "布林通道",
        "category": "波動",
        "score": 0,
        "status": "中軌下方",
        "reason": "價格位於布林中軌下方。",
        "risk": 0,
    }