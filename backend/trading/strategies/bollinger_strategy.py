import pandas as pd
import ta


def signal(df: pd.DataFrame, window: int = 20, num_std: float = 2.0) -> str:
    """
    Buy quand le prix croise sous la bande inférieure (survente).
    Sell quand il croise au-dessus de la bande supérieure (surachat).
    """
    if len(df) < window:
        return "hold"

    bb = ta.volatility.BollingerBands(df["close"], window=window, window_dev=num_std)
    lower = bb.bollinger_lband()
    upper = bb.bollinger_hband()
    price = df["close"]

    if price.iloc[-2] >= lower.iloc[-2] and price.iloc[-1] < lower.iloc[-1]:
        return "buy"
    if price.iloc[-2] <= upper.iloc[-2] and price.iloc[-1] > upper.iloc[-1]:
        return "sell"
    return "hold"
