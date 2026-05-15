import pandas as pd
import ta
from sqlalchemy.orm import Session

from models.strategy_config import StrategyConfig
from models.portfolio import Position
from models.snapshot import PortfolioSnapshot
from models.trade import Trade, TradeAction, TradeStatus, AssetType
from trading.engine import fetch_ohlcv
from brokers.alpaca_broker import AlpacaBroker
from brokers.binance_broker import BinanceBroker
from notifications import telegram

MAX_POSITIONS = 10
TOP_N = 3
REBALANCE_THRESHOLD = 0.20
INITIAL_CAPITAL = 10_000.0
GLOBAL_STOP_LOSS_PCT = 0.05
STOP_LOSS_THRESHOLD = INITIAL_CAPITAL * (1 - GLOBAL_STOP_LOSS_PCT)  # 9 500$


# ── Scoring ───────────────────────────────────────────────────────────

def _score_rsi(df: pd.DataFrame, params: dict) -> tuple[str, float]:
    period = params.get("period", 14)
    oversold = params.get("oversold", 30)
    overbought = params.get("overbought", 70)
    if len(df) < period + 1:
        return "hold", 0.0
    rsi = ta.momentum.RSIIndicator(df["close"], window=period).rsi().iloc[-1]
    if rsi < oversold:
        return "buy", round((oversold - rsi) / oversold, 3)
    if rsi > overbought:
        return "sell", round((rsi - overbought) / (100 - overbought), 3)
    return "hold", 0.0


def _score_ma_crossover(df: pd.DataFrame, params: dict) -> tuple[str, float]:
    short_w = params.get("short_window", 20)
    long_w = params.get("long_window", 50)
    if len(df) < long_w:
        return "hold", 0.0
    ma_short = df["close"].rolling(short_w).mean().iloc[-1]
    ma_long = df["close"].rolling(long_w).mean().iloc[-1]
    gap = (ma_short - ma_long) / ma_long
    if gap > 0:
        return "buy", round(min(abs(gap) * 20, 1.0), 3)
    if gap < 0:
        return "sell", round(min(abs(gap) * 20, 1.0), 3)
    return "hold", 0.0


def _score_macd(df: pd.DataFrame, params: dict) -> tuple[str, float]:
    fast = params.get("fast", 12)
    slow = params.get("slow", 26)
    signal_period = params.get("signal_period", 9)
    if len(df) < slow + signal_period:
        return "hold", 0.0
    macd = ta.trend.MACD(df["close"], window_fast=fast, window_slow=slow, window_sign=signal_period)
    macd_line = macd.macd().iloc[-1]
    signal_line = macd.macd_signal().iloc[-1]
    gap = macd_line - signal_line
    if gap > 0:
        return "buy", round(min(abs(gap) / (df["close"].iloc[-1] * 0.01), 1.0), 3)
    if gap < 0:
        return "sell", round(min(abs(gap) / (df["close"].iloc[-1] * 0.01), 1.0), 3)
    return "hold", 0.0


def _score_bollinger(df: pd.DataFrame, params: dict) -> tuple[str, float]:
    window = params.get("window", 20)
    num_std = params.get("num_std", 2.0)
    if len(df) < window:
        return "hold", 0.0
    bb = ta.volatility.BollingerBands(df["close"], window=window, window_dev=num_std)
    price = df["close"].iloc[-1]
    lower = bb.bollinger_lband().iloc[-1]
    upper = bb.bollinger_hband().iloc[-1]
    mid = bb.bollinger_mavg().iloc[-1]
    band_width = upper - lower
    if band_width == 0:
        return "hold", 0.0
    if price < lower:
        return "buy", round(min((lower - price) / band_width, 1.0), 3)
    if price > upper:
        return "sell", round(min((price - upper) / band_width, 1.0), 3)
    return "hold", 0.0


SCORERS = {
    "RSI": _score_rsi,
    "MA Crossover": _score_ma_crossover,
    "MACD": _score_macd,
    "Bollinger Bands": _score_bollinger,
}


def _score_config(config: StrategyConfig) -> tuple[str, float]:
    scorer = SCORERS.get(config.name)
    if not scorer:
        return "hold", 0.0
    df = fetch_ohlcv(config.symbol, config.asset_type)
    if df.empty:
        return "hold", 0.0
    return scorer(df, config.params or {})


# ── P&L ──────────────────────────────────────────────────────────────

def _compute_realized_pnl(db: Session) -> float:
    sells = db.query(Trade).filter(
        Trade.action == TradeAction.sell,
        Trade.status == TradeStatus.filled,
        Trade.price.isnot(None),
    ).all()
    buys = db.query(Trade).filter(
        Trade.action == TradeAction.buy,
        Trade.status == TradeStatus.filled,
        Trade.price.isnot(None),
    ).all()
    revenue = sum(t.price * t.quantity for t in sells)
    cost = sum(t.price * t.quantity for t in buys)
    return round(revenue - cost, 2)


# ── Snapshot ──────────────────────────────────────────────────────────

def take_snapshot(db: Session) -> None:
    positions = db.query(Position).all()
    capital_deployed = sum(p.capital_allocated for p in positions)
    realized_pnl = _compute_realized_pnl(db)
    portfolio_value = INITIAL_CAPITAL + realized_pnl

    snapshot = PortfolioSnapshot(
        portfolio_value=portfolio_value,
        open_positions=len(positions),
        realized_pnl=realized_pnl,
        capital_deployed=capital_deployed,
    )
    db.add(snapshot)
    db.commit()


# ── Broker helpers ────────────────────────────────────────────────────

def _broker(asset_type: str):
    return AlpacaBroker() if asset_type == "stock" else BinanceBroker()


def _record_trade(db: Session, symbol: str, asset_type: str, action: str,
                  quantity: float, price: float, strategy: str,
                  status: str, order_id: str = None) -> None:
    trade = Trade(
        symbol=symbol,
        asset_type=AssetType(asset_type),
        action=TradeAction(action),
        quantity=quantity,
        price=price,
        strategy=strategy,
        status=TradeStatus(status),
        broker_order_id=order_id,
    )
    db.add(trade)


# ── Close position ────────────────────────────────────────────────────

def _close_position(position: Position, db: Session) -> None:
    try:
        broker = _broker(position.asset_type)
        price = broker.get_latest_price(position.symbol)
        result = broker.place_order(position.symbol, position.quantity, "sell")
        pnl = round((price - position.entry_price) * position.quantity, 2)
        _record_trade(db, position.symbol, position.asset_type, "sell",
                      position.quantity, price, position.strategy,
                      "filled", result["broker_order_id"])
        telegram.alert_trade_close(position.symbol, position.strategy,
                                   position.quantity, price, pnl)
        db.delete(position)
    except Exception as e:
        _record_trade(db, position.symbol, position.asset_type, "sell",
                      position.quantity, 0, position.strategy, "failed")
        telegram.alert_error(position.symbol, "vente", str(e))


# ── Stop-loss global ──────────────────────────────────────────────────

def _check_global_stop_loss(db: Session) -> bool:
    """Retourne True si le stop-loss global est déclenché."""
    realized_pnl = _compute_realized_pnl(db)
    portfolio_value = INITIAL_CAPITAL + realized_pnl
    return portfolio_value < STOP_LOSS_THRESHOLD


def _close_all_positions(db: Session) -> None:
    positions = db.query(Position).all()
    for position in positions:
        _close_position(position, db)
    db.flush()


# ── Portfolio manager ─────────────────────────────────────────────────

def run_portfolio(db: Session) -> None:
    # Stop-loss global — coupe tout si perte > 5%
    if _check_global_stop_loss(db):
        positions = db.query(Position).all()
        if positions:
            realized_pnl = _compute_realized_pnl(db)
            portfolio_value = INITIAL_CAPITAL + realized_pnl
            _close_all_positions(db)
            telegram.alert_global_stop_loss(portfolio_value, STOP_LOSS_THRESHOLD, GLOBAL_STOP_LOSS_PCT * 100)
        take_snapshot(db)
        return

    configs = db.query(StrategyConfig).filter(StrategyConfig.enabled == True).all()
    if not configs:
        return

    # 1. Score tous les actifs
    scored = []
    for config in configs:
        action, score = _score_config(config)
        if action == "buy" and score > 0:
            scored.append((score, config))
    scored.sort(key=lambda x: x[0], reverse=True)

    top_candidates = scored[:MAX_POSITIONS]
    top_n = top_candidates[:TOP_N]
    top_symbols = {c.symbol for _, c in top_n}

    current_positions = db.query(Position).all()
    current_symbols = {p.symbol: p for p in current_positions}

    # 2. Rééquilibrage — ferme si un signal est 20% plus fort
    if top_candidates:
        best_available_score = next(
            (score for score, c in top_candidates if c.symbol not in current_symbols),
            0,
        )
        for position in list(current_positions):
            pos_score = next(
                (score for score, c in scored if c.symbol == position.symbol), 0
            )
            should_replace = (
                position.symbol not in top_symbols
                and best_available_score > pos_score * (1 + REBALANCE_THRESHOLD)
                and len(current_symbols) >= TOP_N
            )
            if should_replace:
                best_candidate = next(
                    (c.symbol for _, c in top_n if c.symbol not in current_symbols), "—"
                )
                telegram.alert_rebalance(
                    position.symbol, best_candidate,
                    f"signal {round(best_available_score * 100)}% > {round(pos_score * 100)}% (+20% seuil)"
                )
                _close_position(position, db)
                del current_symbols[position.symbol]

    db.flush()

    # 3. Ouvre les nouvelles positions top N
    current_positions = db.query(Position).all()
    current_symbols = {p.symbol for p in current_positions}
    open_slots = TOP_N - len(current_symbols)

    if open_slots <= 0:
        db.commit()
        take_snapshot(db)
        return

    capital_per_slot = INITIAL_CAPITAL / TOP_N

    for score, config in top_n:
        if config.symbol in current_symbols or open_slots <= 0:
            continue
        try:
            broker = _broker(config.asset_type)
            price = broker.get_latest_price(config.symbol)
            quantity = round(capital_per_slot / price, 6)
            if quantity <= 0:
                continue

            result = broker.place_order(config.symbol, quantity, "buy")
            _record_trade(db, config.symbol, config.asset_type, "buy",
                          quantity, price, config.name,
                          "filled", result["broker_order_id"])

            position = Position(
                symbol=config.symbol,
                asset_type=config.asset_type,
                strategy=config.name,
                quantity=quantity,
                entry_price=price,
                capital_allocated=capital_per_slot,
                score=float(score),
            )
            db.add(position)
            current_symbols.add(config.symbol)
            open_slots -= 1

            telegram.alert_trade_open(config.symbol, config.name,
                                      quantity, price, score)
        except Exception as e:
            _record_trade(db, config.symbol, config.asset_type, "buy",
                          0, 0, config.name, "failed")
            telegram.alert_error(config.symbol, "achat", str(e))

    db.commit()
    take_snapshot(db)
