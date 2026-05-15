import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.routes import auth_router, limiter, router
from core.config import settings
from core.logging_config import setup_logging
from models.base import Base, engine
import models.portfolio  # enregistre la table Position
import models.snapshot   # enregistre la table PortfolioSnapshot
from scheduler import job_runner

setup_logging(settings.ENV)
_logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    job_runner.start()
    _logger.info("Trading bot démarré (ENV=%s)", settings.ENV)
    yield
    job_runner.stop()
    _logger.info("Trading bot arrêté")


app = FastAPI(title="Trading Bot API", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

app.include_router(auth_router)
app.include_router(router, prefix="/api")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, HTTPException):
        raise exc
    _logger.exception("Erreur non gérée — %s %s", request.method, request.url.path)
    if settings.ENV == "production":
        return JSONResponse(status_code=500, content={"detail": "Erreur interne du serveur"})
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/health")
def health():
    return {"status": "ok"}
