from sqlalchemy import Column, Integer, String, Float, Boolean, JSON
from models.base import Base


class StrategyConfig(Base):
    __tablename__ = "strategy_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)           # ex: "MA Crossover"
    symbol = Column(String, nullable=False)          # ex: "AAPL", "BTC/USDT"
    asset_type = Column(String, nullable=False)      # "stock" | "crypto"
    enabled = Column(Boolean, default=True)
    params = Column(JSON, default={})               # paramètres spécifiques à la stratégie
    stop_loss_pct = Column(Float, default=5.0)      # % de perte max
    take_profit_pct = Column(Float, default=10.0)   # % de gain cible
    position_size_pct = Column(Float, default=10.0) # % du capital à engager
