from analysis.trend import analyze_trend
from analysis.momentum import analyze_momentum
from analysis.emotion import analyze_emotion
from analysis.volatility import analyze_volatility
from analysis.volume import analyze_volume
from analysis.structure import analyze_structure
from analysis.bos import analyze_bos
from analysis.choch import analyze_choch


def run_pipeline(data):
    current = data.iloc[-1]
    previous = data.iloc[-2]
    price = current["close"]

    score_items = [
        analyze_trend(
            price,
            current["ema20"],
            current["ema60"],
        ),
        analyze_momentum(
            current["macd_hist"],
            previous["macd_hist"],
        ),
        analyze_emotion(
            current["rsi14"],
        ),
        analyze_volatility(
            price,
            current["boll_high"],
            current["boll_mid"],
            current["boll_low"],
        ),
        analyze_volume(data),
        analyze_structure(data),
        analyze_bos(data),
        analyze_choch(data),
    ]

    return score_items