import logging
from datetime import datetime, time
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from models.base import SessionLocal
from trading.portfolio import run_portfolio

_log = logging.getLogger("trading.scheduler")
scheduler = BackgroundScheduler()

_NASDAQ_TZ = ZoneInfo("America/New_York")
_MARKET_OPEN = time(9, 30)
_MARKET_CLOSE = time(16, 0)


def is_market_open() -> bool:
    now = datetime.now(_NASDAQ_TZ)
    if now.weekday() >= 5:
        return False
    return _MARKET_OPEN <= now.time() <= _MARKET_CLOSE


def _run_portfolio_cycle() -> None:
    if not is_market_open():
        return
    _log.debug("scheduler: démarrage du cycle portfolio")
    db: Session = SessionLocal()
    try:
        run_portfolio(db)
        _log.debug("scheduler: cycle terminé")
    except Exception as exc:
        _log.error("scheduler: erreur dans le cycle portfolio — %s", exc, exc_info=True)
    finally:
        db.close()


def start() -> None:
    scheduler.add_job(_run_portfolio_cycle, "interval", minutes=3, id="portfolio_loop")
    scheduler.start()
    _log.info("scheduler: démarré (intervalle 3 min, heures marché Nasdaq)")


def stop() -> None:
    scheduler.shutdown()
    _log.info("scheduler: arrêté")
