from datetime import datetime
from sqlalchemy import Column, Integer, Float, DateTime
from models.base import Base


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    portfolio_value = Column(Float, nullable=False)  # capital initial + P&L réalisé
    open_positions = Column(Integer, default=0)
    realized_pnl = Column(Float, default=0.0)
    capital_deployed = Column(Float, default=0.0)
