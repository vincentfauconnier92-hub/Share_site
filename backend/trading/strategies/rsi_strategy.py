import pandas as pd
import ta


def signal(df: pd.DataFrame, period: int = 14, oversold: int = 30, overbought: int = 70) -> str:
    """
    Retourne 'buy' si RSI < oversold, 'sell' si RSI > overbought, sinon 'hold'.
    """
    if len(df) < period + 1:
        return "hold"

    rsi = ta.momentum.RSIIndicator(df["close"], window=period).rsi()
    current_rsi = rsi.iloc[-1]

    if current_rsi < oversold:
        return "buy"
    if current_rsi > overbought:
        return "sell"
    return "hold"
