import logging
import sys


def setup_logging(env: str = "development") -> None:
    level = logging.DEBUG if env == "development" else logging.INFO
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    # Réduire le bruit des librairies tierces
    for noisy in ("uvicorn.access", "apscheduler", "yfinance", "peewee", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
