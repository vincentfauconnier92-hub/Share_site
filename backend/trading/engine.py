import logging

import pandas as pd
import yfinance as yf
from sqlalchemy.orm import Session

from models.strategy_config import StrategyConfig
from models.trade import Trade, TradeAction, TradeStatus, AssetType
from brokers.alpaca_broker import AlpacaBroker
from brokers.binance_broker import BinanceBroker
from trading.strategies import ma_crossover, rsi_strategy, macd_strategy, bollinger_strategy

_log = logging.getLogger("trading.engine")

STRATEGIES = {
    "MA Crossover": ma_crossover.signal,
    "RSI": rsi_strategy.signal,
    "MACD": macd_strategy.signal,
    "Bollinger Bands": bollinger_strategy.signal,
}


def fetch_ohlcv(symbol: str, asset_type: str, period: str = "60d") -> pd.DataFrame:
    ticker = symbol if asset_type == "stock" else symbol.replace("/", "-")
    df = yf.download(ticker, period=period, interval="1d", progress=False)
    if df.empty:
        _log.warning("fetch_ohlcv: aucune donnée pour %s (period=%s)", symbol, period)
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df.columns = [c.lower() for c in df.columns]
    return df.reset_index()


def run_strategy(config: StrategyConfig, db: Session) -> None:
    strategy_fn = STRATEGIES.get(config.name)
    if not strategy_fn:
        _log.warning("run_strategy: stratégie inconnue '%s'", config.name)
        return

    df = fetch_ohlcv(config.symbol, config.asset_type)
    if df.empty:
        return

    action = strategy_fn(df, **config.params)
    _log.debug("run_strategy: %s/%s → %s", config.name, config.symbol, action)

    if action == "hold":
        return

    broker = AlpacaBroker() if config.asset_type == "stock" else BinanceBroker()
    price = broker.get_latest_price(config.symbol)

    trade = Trade(
        symbol=config.symbol,
        asset_type=AssetType(config.asset_type),
        action=TradeAction(action),
        quantity=config.position_size_pct,
        price=price,
        strategy=config.name,
        status=TradeStatus.pending,
    )

    try:
        result = broker.place_order(config.symbol, config.position_size_pct, action)
        trade.status = TradeStatus.filled
        trade.broker_order_id = result["broker_order_id"]
        _log.info("order.filled symbol=%s action=%s qty=%s price=%.2f",
                  config.symbol, action, config.position_size_pct, price)
    except Exception as exc:
        trade.status = TradeStatus.failed
        _log.error("order.failed symbol=%s action=%s error=%s", config.symbol, action, exc)

    db.add(trade)
    db.commit()
