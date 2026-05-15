import pandas as pd


def signal(df: pd.DataFrame, short_window: int = 20, long_window: int = 50) -> str:
    """
    Retourne 'buy', 'sell' ou 'hold' selon le croisement des moyennes mobiles.
    df doit contenir une colonne 'close'.
    """
    if len(df) < long_window:
        return "hold"

    df = df.copy()
    df["ma_short"] = df["close"].rolling(short_window).mean()
    df["ma_long"] = df["close"].rolling(long_window).mean()

    prev = df.iloc[-2]
    curr = df.iloc[-1]

    if prev["ma_short"] <= prev["ma_long"] and curr["ma_short"] > curr["ma_long"]:
        return "buy"
    if prev["ma_short"] >= prev["ma_long"] and curr["ma_short"] < curr["ma_long"]:
        return "sell"
    return "hold"
