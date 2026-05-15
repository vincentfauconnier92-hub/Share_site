from datetime import datetime, time
from zoneinfo import ZoneInfo
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from models.base import SessionLocal
from trading.portfolio import run_portfolio

scheduler = BackgroundScheduler()

_NASDAQ_TZ = ZoneInfo("America/New_York")
_MARKET_OPEN = time(9, 30)
_MARKET_CLOSE = time(16, 0)


def is_market_open() -> bool:
    now = datetime.now(_NASDAQ_TZ)
    if now.weekday() >= 5:          # samedi / dimanche
        return False
    return _MARKET_OPEN <= now.time() <= _MARKET_CLOSE


def _run_portfolio_cycle():
    if not is_market_open():
        return
    db: Session = SessionLocal()
    try:
        run_portfolio(db)
    finally:
        db.close()


def start():
    scheduler.add_job(_run_portfolio_cycle, "interval", minutes=3, id="portfolio_loop")
    scheduler.start()


def stop():
    scheduler.shutdown()
