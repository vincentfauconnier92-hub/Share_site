from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date, timedelta, datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

from models.base import get_db
from models.trade import Trade
from models.strategy_config import StrategyConfig
from models.portfolio import Position
from models.snapshot import PortfolioSnapshot
from backtest.runner import run_backtest
from trading.portfolio import (
    _score_config, _compute_realized_pnl, _check_global_stop_loss,
    TOP_N, MAX_POSITIONS, REBALANCE_THRESHOLD,
    INITIAL_CAPITAL, GLOBAL_STOP_LOSS_PCT, STOP_LOSS_THRESHOLD,
)
from core.auth import verify_api_key

router = APIRouter(dependencies=[Depends(verify_api_key)])


# ── Trades ────────────────────────────────────────────────────────────

@router.get("/trades")
def list_trades(limit: int = 50, db: Session = Depends(get_db)):
    return db.query(Trade).order_by(Trade.created_at.desc()).limit(limit).all()


# ── Stratégies ────────────────────────────────────────────────────────

class StrategyConfigIn(BaseModel):
    name: str
    symbol: str
    asset_type: str
    enabled: bool = True
    params: dict = {}
    stop_loss_pct: float = 5.0
    take_profit_pct: float = 10.0
    position_size_pct: float = 10.0


@router.get("/strategies")
def list_strategies(db: Session = Depends(get_db)):
    return db.query(StrategyConfig).all()


@router.post("/strategies")
def create_strategy(body: StrategyConfigIn, db: Session = Depends(get_db)):
    config = StrategyConfig(**body.model_dump())
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


class ActivateFromScanRequest(BaseModel):
    symbol: str
    strategy_name: str
    asset_type: str = "stock"


@router.post("/strategies/activate-from-scan")
def activate_from_scan(body: ActivateFromScanRequest, db: Session = Depends(get_db)):
    existing = db.query(StrategyConfig).filter(
        StrategyConfig.symbol == body.symbol,
        StrategyConfig.name == body.strategy_name,
    ).first()
    if existing:
        existing.enabled = True
        db.commit()
        return existing
    config = StrategyConfig(
        name=body.strategy_name,
        symbol=body.symbol,
        asset_type=body.asset_type,
        enabled=True,
        params={},
        stop_loss_pct=5.0,
        take_profit_pct=10.0,
        position_size_pct=10.0,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


@router.patch("/strategies/{strategy_id}")
def update_strategy(strategy_id: int, body: StrategyConfigIn, db: Session = Depends(get_db)):
    config = db.query(StrategyConfig).filter(StrategyConfig.id == strategy_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Stratégie introuvable")
    for key, value in body.model_dump().items():
        setattr(config, key, value)
    db.commit()
    return config


@router.delete("/strategies/{strategy_id}")
def delete_strategy(strategy_id: int, db: Session = Depends(get_db)):
    config = db.query(StrategyConfig).filter(StrategyConfig.id == strategy_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Stratégie introuvable")
    db.delete(config)
    db.commit()
    return {"ok": True}


# ── Portfolio ─────────────────────────────────────────────────────────

@router.get("/portfolio")
def get_portfolio(db: Session = Depends(get_db)):
    positions = db.query(Position).order_by(Position.score.desc()).all()
    configs = db.query(StrategyConfig).filter(StrategyConfig.enabled == True).all()

    scored = []
    for config in configs:
        action, score = _score_config(config)
        scored.append({
            "symbol": config.symbol,
            "strategy": config.name,
            "asset_type": config.asset_type,
            "action": action,
            "score": score,
        })
    scored.sort(key=lambda x: x["score"], reverse=True)

    return {
        "positions": [
            {
                "id": p.id,
                "symbol": p.symbol,
                "asset_type": p.asset_type,
                "strategy": p.strategy,
                "quantity": p.quantity,
                "entry_price": p.entry_price,
                "capital_allocated": p.capital_allocated,
                "score": p.score,
                "opened_at": p.opened_at,
            }
            for p in positions
        ],
        "signals": scored,
        "config": {
            "max_positions": MAX_POSITIONS,
            "top_n": TOP_N,
            "rebalance_threshold_pct": int(REBALANCE_THRESHOLD * 100),
            "stop_loss_pct": int(GLOBAL_STOP_LOSS_PCT * 100),
            "stop_loss_threshold": STOP_LOSS_THRESHOLD,
        },
        "stop_loss_triggered": _check_global_stop_loss(db),
        "portfolio_value": round(INITIAL_CAPITAL + _compute_realized_pnl(db), 2),
    }


@router.get("/portfolio/unrealized")
def get_unrealized_pnl(db: Session = Depends(get_db)):
    from brokers.alpaca_broker import AlpacaBroker
    from brokers.binance_broker import BinanceBroker

    positions = db.query(Position).all()
    realized = _compute_realized_pnl(db)

    if not positions:
        return {
            "positions": [],
            "total_unrealized_pnl": 0.0,
            "realized_pnl": round(realized, 2),
            "mark_to_market_value": round(INITIAL_CAPITAL + realized, 2),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    stock_positions = [p for p in positions if p.asset_type == "stock"]
    crypto_positions = [p for p in positions if p.asset_type == "crypto"]

    price_map: dict[str, float | None] = {}

    if stock_positions:
        try:
            broker = AlpacaBroker()
            prices = broker.get_latest_prices_batch([p.symbol for p in stock_positions])
            price_map.update(prices)
        except Exception:
            for p in stock_positions:
                price_map[p.symbol] = None

    if crypto_positions:
        try:
            broker = BinanceBroker()
            for p in crypto_positions:
                try:
                    price_map[p.symbol] = broker.get_latest_price(p.symbol)
                except Exception:
                    price_map[p.symbol] = None
        except Exception:
            for p in crypto_positions:
                price_map[p.symbol] = None

    result_positions = []
    total_unrealized = 0.0

    for pos in positions:
        current_price = price_map.get(pos.symbol)
        if current_price is not None and pos.entry_price:
            unrealized_pnl = (current_price - pos.entry_price) * pos.quantity
            return_pct = ((current_price - pos.entry_price) / pos.entry_price) * 100
            total_unrealized += unrealized_pnl
        else:
            unrealized_pnl = None
            return_pct = None

        result_positions.append({
            "id": pos.id,
            "symbol": pos.symbol,
            "asset_type": pos.asset_type,
            "strategy": pos.strategy,
            "quantity": pos.quantity,
            "entry_price": pos.entry_price,
            "current_price": round(current_price, 4) if current_price is not None else None,
            "unrealized_pnl": round(unrealized_pnl, 2) if unrealized_pnl is not None else None,
            "return_pct": round(return_pct, 2) if return_pct is not None else None,
            "capital_allocated": pos.capital_allocated,
            "opened_at": pos.opened_at,
        })

    return {
        "positions": result_positions,
        "total_unrealized_pnl": round(total_unrealized, 2),
        "realized_pnl": round(realized, 2),
        "mark_to_market_value": round(INITIAL_CAPITAL + realized + total_unrealized, 2),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/portfolio/history")
def get_portfolio_history(limit: int = 500, db: Session = Depends(get_db)):
    snapshots = (
        db.query(PortfolioSnapshot)
        .order_by(PortfolioSnapshot.timestamp.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "timestamp": s.timestamp.isoformat(),
            "portfolio_value": round(s.portfolio_value, 2),
            "open_positions": s.open_positions,
            "realized_pnl": round(s.realized_pnl, 2),
            "capital_deployed": round(s.capital_deployed, 2),
        }
        for s in snapshots
    ]


# ── Backtesting ───────────────────────────────────────────────────────

class BacktestRequest(BaseModel):
    symbol: str
    asset_type: str
    strategy_name: str
    start_date: str
    end_date: str
    params: dict = {}
    cash: float = 10_000


@router.post("/backtest")
def launch_backtest(body: BacktestRequest):
    try:
        result = run_backtest(
            symbol=body.symbol,
            asset_type=body.asset_type,
            strategy_name=body.strategy_name,
            start_date=body.start_date,
            end_date=body.end_date,
            params=body.params,
            cash=body.cash,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Scanner ───────────────────────────────────────────────────────────

NASDAQ_100 = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "AVGO", "COST", "NFLX",
    "AMD",  "ADBE", "QCOM", "INTC", "TXN",  "AMAT",  "MU",   "INTU", "LRCX", "KLAC",
    "MRVL", "PANW", "SNPS", "CDNS", "REGN", "VRTX",  "GILD", "AMGN", "ISRG", "MDLZ",
    "ADI",  "MELI", "ORLY", "CTAS", "MNST", "WDAY",  "TEAM", "DXCM", "ABNB", "CRWD",
    "ZS",   "FTNT", "PCAR", "PAYX", "FAST", "IDXX",  "LULU", "MAR",  "MRNA", "NXPI",
    "ON",   "ROST", "SBUX", "SMCI", "VRSK", "GEHC",  "GFS",  "KHC",  "ODFL", "PDD",
    "TTD",  "FANG", "CCEP", "CPRT", "CSGP", "DDOG",  "DLTR", "EA",   "EXC",  "EXPE",
    "FSLR", "HON",  "ILMN", "KDP",  "LCID", "MCHP",  "MDLZ", "NXPI", "PYPL", "SIRI",
    "TTWO", "WBD",  "XEL",  "ZM",   "BIIB", "BMRN",  "CELH", "CINF", "CSX",  "EBAY",
    "ENPH", "HOOD", "MDB",  "NTNX", "OKTA", "RIVN",  "SNOW", "UBER", "VEEV", "ZI",
]

STRATEGY_NAMES = ["MA Crossover", "RSI", "MACD", "Bollinger Bands"]

PERIODS = {
    "1an":  (365,  "1 an"),
    "3ans": (1095, "3 ans"),
}


class ScanRequest(BaseModel):
    symbols: list[str] = NASDAQ_100
    periods: list[str] = ["1an", "3ans"]
    cash: float = 10_000


def _run_one(symbol: str, strategy: str, period_key: str, cash: float) -> dict | None:
    days, label = PERIODS[period_key]
    end = date.today()
    start = end - timedelta(days=days)
    try:
        result = run_backtest(
            symbol=symbol,
            asset_type="stock",
            strategy_name=strategy,
            start_date=str(start),
            end_date=str(end),
            cash=cash,
        )
        result["period_label"] = label
        return result
    except Exception:
        return None


def _estimate_scan_duration(n_symbols: int, n_periods: int) -> str:
    total = n_symbols * len(STRATEGY_NAMES) * n_periods
    seconds = total * 1.5
    if seconds < 60:
        return f"~{int(seconds)} secondes"
    return f"~{int(seconds / 60)} minutes"


@router.get("/backtest/scan/nasdaq100")
def get_nasdaq100():
    return {"symbols": NASDAQ_100, "count": len(NASDAQ_100)}


@router.post("/backtest/scan")
def scan_backtests(body: ScanRequest):
    tasks = [
        (symbol, strategy, period)
        for symbol in body.symbols
        for strategy in STRATEGY_NAMES
        for period in body.periods
        if period in PERIODS
    ]

    results = []
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = {
            pool.submit(_run_one, symbol, strategy, period, body.cash): (symbol, strategy, period)
            for symbol, strategy, period in tasks
        }
        for future in as_completed(futures):
            result = future.result()
            if result and result["num_trades"] > 0:
                results.append(result)

    results.sort(key=lambda r: r["sharpe_ratio"], reverse=True)
    return results


# ── Optimisation ──────────────────────────────────────────────────────

PARAM_GRIDS = {
    "MA Crossover": [
        {"short_window": s, "long_window": l}
        for s in [10, 20, 30]
        for l in [40, 50, 100]
        if s < l
    ],
    "RSI": [
        {"period": p, "oversold": os, "overbought": ob}
        for p in [7, 14, 21]
        for os in [25, 30]
        for ob in [70, 75]
    ],
    "MACD": [
        {"fast": f, "slow": sl, "signal_period": sg}
        for f in [8, 12]
        for sl in [21, 26]
        for sg in [7, 9]
        if f < sl
    ],
    "Bollinger Bands": [
        {"window": w, "num_std": s}
        for w in [10, 20, 30]
        for s in [1.5, 2.0, 2.5]
    ],
}


class OptimizeRequest(BaseModel):
    symbol: str
    asset_type: str = "stock"
    strategy_name: str
    period: str = "1an"
    cash: float = 10_000


def _run_with_params(symbol: str, asset_type: str, strategy: str,
                     start: str, end: str, params: dict, cash: float) -> dict | None:
    try:
        result = run_backtest(
            symbol=symbol, asset_type=asset_type, strategy_name=strategy,
            start_date=start, end_date=end, params=params, cash=cash,
        )
        result["params"] = params
        return result
    except Exception:
        return None


@router.post("/backtest/optimize")
def optimize_strategy(body: OptimizeRequest):
    grid = PARAM_GRIDS.get(body.strategy_name)
    if not grid:
        raise HTTPException(status_code=400, detail=f"Stratégie inconnue : {body.strategy_name}")

    days = PERIODS.get(body.period, (365, "1 an"))[0]
    end = str(date.today())
    start = str(date.today() - timedelta(days=days))

    results = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(_run_with_params, body.symbol, body.asset_type,
                        body.strategy_name, start, end, params, body.cash): params
            for params in grid
        }
        for future in as_completed(futures):
            result = future.result()
            if result and result["num_trades"] > 0:
                results.append(result)

    if not results:
        raise HTTPException(status_code=404, detail="Aucun résultat pour ces paramètres.")

    results.sort(key=lambda r: r["sharpe_ratio"], reverse=True)
    return {
        "best": results[0],
        "all": results,
        "symbol": body.symbol,
        "strategy": body.strategy_name,
        "period": body.period,
        "combinations_tested": len(grid),
    }
