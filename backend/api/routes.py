import logging
import re
from datetime import date, datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Literal

_audit = logging.getLogger("trading.audit")

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field, field_validator, model_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from backtest.runner import run_backtest
from core.auth import create_access_token, verify_api_key
from core.config import settings
from models.base import get_db
from models.portfolio import Position
from models.snapshot import PortfolioSnapshot
from models.strategy_config import StrategyConfig
from models.trade import Trade
from trading.portfolio import (
    GLOBAL_STOP_LOSS_PCT,
    INITIAL_CAPITAL,
    MAX_POSITIONS,
    REBALANCE_THRESHOLD,
    STOP_LOSS_THRESHOLD,
    TOP_N,
    _check_global_stop_loss,
    _compute_realized_pnl,
    _score_config,
    compute_portfolio_value,
)

limiter = Limiter(key_func=get_remote_address)

# ── Constantes de validation ──────────────────────────────────────────

_SYMBOL_RE = re.compile(r"^[A-Z0-9\-\/]{1,15}$")
_VALID_STRATEGIES = frozenset({"MA Crossover", "RSI", "MACD", "Bollinger Bands"})
_ALLOWED_PARAMS: dict[str, set[str]] = {
    "MA Crossover": {"short_window", "long_window"},
    "RSI": {"period", "oversold", "overbought"},
    "MACD": {"fast", "slow", "signal_period"},
    "Bollinger Bands": {"window", "num_std"},
}


def _check_symbol(v: str) -> str:
    v = v.strip().upper()
    if not _SYMBOL_RE.match(v):
        raise ValueError("Symbole invalide — lettres majuscules, chiffres, - ou / uniquement (max 15 chars)")
    return v


def _check_date(v: str) -> str:
    try:
        datetime.strptime(v, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Format de date invalide — YYYY-MM-DD requis")
    return v


def _check_params(params: dict, strategy_name: str) -> dict:
    allowed = _ALLOWED_PARAMS.get(strategy_name, set())
    for key, val in params.items():
        if key not in allowed:
            raise ValueError(f"Paramètre '{key}' non autorisé pour '{strategy_name}'")
        if not isinstance(val, (int, float)) or val <= 0:
            raise ValueError(f"Paramètre '{key}' doit être un nombre strictement positif")
    return params


# ── Auth (non protégé, rate-limité) ──────────────────────────────────

auth_router = APIRouter()


@auth_router.post("/auth/token")
@limiter.limit("10/minute")
def get_token(request: Request, x_api_key: str = Header(...)):
    """Échange la clé API contre un JWT à durée limitée."""
    ip = request.client.host if request.client else "unknown"
    if not settings.API_SECRET_KEY or x_api_key != settings.API_SECRET_KEY:
        _audit.warning("auth.token_denied ip=%s", ip)
        raise HTTPException(status_code=401, detail="Clé API invalide")
    token = create_access_token()
    _audit.info("auth.token_issued ip=%s expires_h=%d", ip, settings.JWT_EXPIRE_HOURS)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.JWT_EXPIRE_HOURS * 3600,
    }


# ── Routes protégées ──────────────────────────────────────────────────

router = APIRouter(dependencies=[Depends(verify_api_key)])


# ── Trades ────────────────────────────────────────────────────────────

@router.get("/trades")
@limiter.limit("60/minute")
def list_trades(request: Request, limit: int = Field(default=50, ge=1, le=500), db: Session = Depends(get_db)):
    return db.query(Trade).order_by(Trade.created_at.desc()).limit(limit).all()


# ── Stratégies ────────────────────────────────────────────────────────

class StrategyConfigIn(BaseModel):
    name: Literal["MA Crossover", "RSI", "MACD", "Bollinger Bands"]
    symbol: str
    asset_type: Literal["stock", "crypto"]
    enabled: bool = True
    params: dict = {}
    stop_loss_pct: float = Field(default=5.0, ge=0.1, le=50.0)
    take_profit_pct: float = Field(default=10.0, ge=0.1, le=100.0)
    position_size_pct: float = Field(default=10.0, ge=0.1, le=10.0)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return _check_symbol(v)

    @model_validator(mode="after")
    def validate_params(self) -> "StrategyConfigIn":
        if self.params:
            _check_params(self.params, self.name)
        return self


class ActivateFromScanRequest(BaseModel):
    symbol: str
    strategy_name: Literal["MA Crossover", "RSI", "MACD", "Bollinger Bands"]
    asset_type: Literal["stock", "crypto"] = "stock"

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return _check_symbol(v)


@router.get("/strategies")
@limiter.limit("60/minute")
def list_strategies(request: Request, db: Session = Depends(get_db)):
    return db.query(StrategyConfig).all()


@router.post("/strategies")
@limiter.limit("30/minute")
def create_strategy(request: Request, body: StrategyConfigIn, db: Session = Depends(get_db)):
    config = StrategyConfig(**body.model_dump())
    db.add(config)
    db.commit()
    db.refresh(config)
    _audit.info("strategy.create id=%d name=%s symbol=%s ip=%s",
                config.id, config.name, config.symbol,
                request.client.host if request.client else "unknown")
    return config


@router.post("/strategies/activate-from-scan")
@limiter.limit("30/minute")
def activate_from_scan(request: Request, body: ActivateFromScanRequest, db: Session = Depends(get_db)):
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
@limiter.limit("30/minute")
def update_strategy(request: Request, strategy_id: int, body: StrategyConfigIn, db: Session = Depends(get_db)):
    config = db.query(StrategyConfig).filter(StrategyConfig.id == strategy_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Stratégie introuvable")
    previous = f"name={config.name} symbol={config.symbol} enabled={config.enabled}"
    for key, value in body.model_dump().items():
        setattr(config, key, value)
    db.commit()
    _audit.info("strategy.update id=%d %s -> name=%s symbol=%s enabled=%s ip=%s",
                strategy_id, previous, config.name, config.symbol, config.enabled,
                request.client.host if request.client else "unknown")
    return config


@router.delete("/strategies/{strategy_id}")
@limiter.limit("30/minute")
def delete_strategy(request: Request, strategy_id: int, db: Session = Depends(get_db)):
    config = db.query(StrategyConfig).filter(StrategyConfig.id == strategy_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Stratégie introuvable")
    _audit.warning("strategy.delete id=%d name=%s symbol=%s ip=%s",
                   strategy_id, config.name, config.symbol,
                   request.client.host if request.client else "unknown")
    db.delete(config)
    db.commit()
    return {"ok": True}


# ── Portfolio ─────────────────────────────────────────────────────────

@router.get("/portfolio")
@limiter.limit("30/minute")
def get_portfolio(request: Request, db: Session = Depends(get_db)):
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
        "portfolio_value": compute_portfolio_value(db),
    }


@router.get("/portfolio/unrealized")
@limiter.limit("30/minute")
def get_unrealized_pnl(request: Request, db: Session = Depends(get_db)):
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
@limiter.limit("30/minute")
def get_portfolio_history(request: Request, limit: int = 500, db: Session = Depends(get_db)):
    snapshots = (
        db.query(PortfolioSnapshot)
        .order_by(PortfolioSnapshot.timestamp.asc())
        .limit(min(limit, 1000))
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
    asset_type: Literal["stock", "crypto"]
    strategy_name: Literal["MA Crossover", "RSI", "MACD", "Bollinger Bands"]
    start_date: str
    end_date: str
    params: dict = {}
    cash: float = Field(default=10_000, gt=0, le=10_000_000)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return _check_symbol(v)

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        return _check_date(v)

    @model_validator(mode="after")
    def validate_date_range(self) -> "BacktestRequest":
        start = datetime.strptime(self.start_date, "%Y-%m-%d")
        end = datetime.strptime(self.end_date, "%Y-%m-%d")
        if start >= end:
            raise ValueError("start_date doit être antérieure à end_date")
        if end.date() > date.today():
            raise ValueError("end_date ne peut pas être dans le futur")
        if start < datetime(1990, 1, 1):
            raise ValueError("Données non disponibles avant 1990")
        if (end - start).days > 10 * 365:
            raise ValueError("Période maximale : 10 ans")
        if self.params:
            _check_params(self.params, self.strategy_name)
        return self


@router.post("/backtest")
@limiter.limit("20/hour")
def launch_backtest(request: Request, body: BacktestRequest):
    try:
        return run_backtest(
            symbol=body.symbol,
            asset_type=body.asset_type,
            strategy_name=body.strategy_name,
            start_date=body.start_date,
            end_date=body.end_date,
            params=body.params,
            cash=body.cash,
        )
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
    cash: float = Field(default=10_000, gt=0, le=10_000_000)

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, v: list[str]) -> list[str]:
        if len(v) > 150:
            raise ValueError("Maximum 150 symboles par scan")
        return [_check_symbol(s) for s in v]

    @field_validator("periods")
    @classmethod
    def validate_periods(cls, v: list[str]) -> list[str]:
        invalid = [p for p in v if p not in PERIODS]
        if invalid:
            raise ValueError(f"Périodes invalides : {invalid}. Valeurs acceptées : {list(PERIODS.keys())}")
        return v


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
@limiter.limit("60/minute")
def get_nasdaq100(request: Request):
    return {"symbols": NASDAQ_100, "count": len(NASDAQ_100)}


@router.post("/backtest/scan")
@limiter.limit("2/hour")
def scan_backtests(request: Request, body: ScanRequest):
    _audit.info("scan.start symbols=%d periods=%s ip=%s",
                len(body.symbols), body.periods,
                request.client.host if request.client else "unknown")
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
    asset_type: Literal["stock", "crypto"] = "stock"
    strategy_name: Literal["MA Crossover", "RSI", "MACD", "Bollinger Bands"]
    period: str = "1an"
    cash: float = Field(default=10_000, gt=0, le=10_000_000)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return _check_symbol(v)

    @field_validator("period")
    @classmethod
    def validate_period(cls, v: str) -> str:
        if v not in PERIODS:
            raise ValueError(f"Période invalide. Valeurs acceptées : {list(PERIODS.keys())}")
        return v


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
@limiter.limit("10/hour")
def optimize_strategy(request: Request, body: OptimizeRequest):
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
