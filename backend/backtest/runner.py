import pandas as pd
import yfinance as yf
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import ta


def _fetch(symbol: str, asset_type: str, start: str, end: str) -> pd.DataFrame:
    ticker = symbol if asset_type == "stock" else symbol.replace("/", "-")
    df = yf.download(ticker, start=start, end=end, progress=False)
    if df.empty:
        return df
    # yfinance 1.x retourne un MultiIndex (Price, Ticker) — on garde juste le niveau Price
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df.columns = [c.capitalize() for c in df.columns]
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    return df


class _MACrossover(Strategy):
    short_window = 20
    long_window = 50

    def init(self):
        self.ma_short = self.I(lambda c: pd.Series(c).rolling(self.short_window).mean(), self.data.Close)
        self.ma_long = self.I(lambda c: pd.Series(c).rolling(self.long_window).mean(), self.data.Close)

    def next(self):
        if crossover(self.ma_short, self.ma_long):
            self.buy()
        elif crossover(self.ma_long, self.ma_short):
            self.sell()


class _RSIStrategy(Strategy):
    rsi_period = 14
    oversold = 30
    overbought = 70

    def init(self):
        self.rsi = self.I(
            lambda c: ta.momentum.RSIIndicator(pd.Series(c), window=self.rsi_period).rsi().values,
            self.data.Close,
        )

    def next(self):
        if self.rsi[-1] < self.oversold:
            self.buy()
        elif self.rsi[-1] > self.overbought:
            self.sell()


class _MACDStrategy(Strategy):
    fast = 12
    slow = 26
    signal_period = 9

    def init(self):
        def _macd(close):
            s = pd.Series(close)
            ema_fast = s.ewm(span=self.fast, adjust=False).mean()
            ema_slow = s.ewm(span=self.slow, adjust=False).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=self.signal_period, adjust=False).mean()
            return macd_line.values, signal_line.values

        result = self.I(_macd, self.data.Close, overlay=False)
        self.macd_line = result[0]
        self.signal_line = result[1]

    def next(self):
        if crossover(self.macd_line, self.signal_line):
            self.buy()
        elif crossover(self.signal_line, self.macd_line):
            self.sell()


class _BollingerStrategy(Strategy):
    window = 20
    num_std = 2.0

    def init(self):
        def _bands(close):
            s = pd.Series(close)
            mid = s.rolling(self.window).mean()
            std = s.rolling(self.window).std()
            return (mid - self.num_std * std).values, (mid + self.num_std * std).values

        bands = self.I(_bands, self.data.Close, overlay=True)
        self.lower = bands[0]
        self.upper = bands[1]

    def next(self):
        if self.data.Close[-1] < self.lower[-1]:
            self.buy()
        elif self.data.Close[-1] > self.upper[-1]:
            self.sell()


STRATEGY_MAP = {
    "MA Crossover": _MACrossover,
    "RSI": _RSIStrategy,
    "MACD": _MACDStrategy,
    "Bollinger Bands": _BollingerStrategy,
}


def run_backtest(
    symbol: str,
    asset_type: str,
    strategy_name: str,
    start_date: str,
    end_date: str,
    params: dict = {},
    cash: float = 10_000,
) -> dict:
    df = _fetch(symbol, asset_type, start_date, end_date)
    if df.empty:
        raise ValueError(f"Aucune donnée pour {symbol} sur la période demandée.")

    strategy_cls = STRATEGY_MAP.get(strategy_name)
    if not strategy_cls:
        raise ValueError(f"Stratégie inconnue : {strategy_name}")

    bt = Backtest(df, strategy_cls, cash=cash, commission=0.001)
    stats = bt.run(**params)

    return {
        "return_pct": round(float(stats["Return [%]"]), 2),
        "max_drawdown_pct": round(float(stats["Max. Drawdown [%]"]), 2),
        "num_trades": int(stats["# Trades"]),
        "win_rate_pct": round(float(stats["Win Rate [%]"]) if stats["# Trades"] > 0 else 0, 2),
        "sharpe_ratio": round(float(stats["Sharpe Ratio"]), 3),
        "start": start_date,
        "end": end_date,
        "symbol": symbol,
        "strategy": strategy_name,
    }
