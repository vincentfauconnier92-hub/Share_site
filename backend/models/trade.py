from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum
import enum
from models.base import Base


class AssetType(str, enum.Enum):
    stock = "stock"
    crypto = "crypto"


class TradeAction(str, enum.Enum):
    buy = "buy"
    sell = "sell"


class TradeStatus(str, enum.Enum):
    pending = "pending"
    filled = "filled"
    cancelled = "cancelled"
    failed = "failed"


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False)
    asset_type = Column(Enum(AssetType), nullable=False)
    action = Column(Enum(TradeAction), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=True)
    status = Column(Enum(TradeStatus), default=TradeStatus.pending)
    strategy = Column(String, nullable=True)
    broker_order_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    filled_at = Column(DateTime, nullable=True)
