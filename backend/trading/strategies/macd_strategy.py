import pandas as pd
import ta


def signal(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal_period: int = 9) -> str:
    """
    Buy quand la ligne MACD croise au-dessus de la ligne signal.
    Sell quand elle croise en dessous.
    """
    if len(df) < slow + signal_period:
        return "hold"

    macd = ta.trend.MACD(df["close"], window_fast=fast, window_slow=slow, window_sign=signal_period)
    macd_line = macd.macd()
    signal_line = macd.macd_signal()

    if macd_line.iloc[-2] <= signal_line.iloc[-2] and macd_line.iloc[-1] > signal_line.iloc[-1]:
        return "buy"
    if macd_line.iloc[-2] >= signal_line.iloc[-2] and macd_line.iloc[-1] < signal_line.iloc[-1]:
        return "sell"
    return "hold"
