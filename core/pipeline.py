from analysis.trend import analyze_trend
from analysis.momentum import analyze_momentum
from analysis.emotion import analyze_emotion
from analysis.volatility import analyze_volatility
from analysis.volume import analyze_volume
from analysis.structure import analyze_structure
from analysis.bos import analyze_bos
from analysis.choch import analyze_choch
from analysis.liquidity import analyze_liquidity
from analysis.order_block import analyze_order_block
from analysis.fvg import analyze_fvg


def run_pipeline(data):
    """
    執行完整交易分析 Pipeline。

    分析順序：
    1. 趨勢
    2. 動能
    3. 市場情緒
    4. 波動率
    5. 成交量
    6. 市場結構
    7. BOS
    8. CHOCH
    9. Liquidity Sweep
    10. Order Block
    11. Fair Value Gap
    """

    if data is None or len(data) < 3:
        raise ValueError(
            "Pipeline 至少需要 3 根 K 棒資料。"
        )

    current = data.iloc[-1]
    previous = data.iloc[-2]

    price = float(current["close"])

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
        analyze_liquidity(data),
        analyze_order_block(data),
        analyze_fvg(data),
    ]

    return score_items