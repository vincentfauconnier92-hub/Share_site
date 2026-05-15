from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.routes import auth_router, limiter, router
from core.config import settings
from models.base import Base, engine
import models.portfolio  # enregistre la table Position
import models.snapshot   # enregistre la table PortfolioSnapshot
from scheduler import job_runner


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    job_runner.start()
    yield
    job_runner.stop()


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


@app.get("/health")
def health():
    return {"status": "ok"}
