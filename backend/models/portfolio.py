from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime
from models.base import Base


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False, unique=True)
    asset_type = Column(String, nullable=False)
    strategy = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    capital_allocated = Column(Float, nullable=False)
    score = Column(Float, nullable=False)
    opened_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
