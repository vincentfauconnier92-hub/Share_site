"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-01
"""
import sqlalchemy as sa
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trades",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("symbol", sa.String, nullable=False, index=True),
        sa.Column("asset_type", sa.String, nullable=False),
        sa.Column("action", sa.String, nullable=False),
        sa.Column("quantity", sa.Float, nullable=False),
        sa.Column("price", sa.Float, nullable=True),
        sa.Column("strategy", sa.String, nullable=True),
        sa.Column("status", sa.String, nullable=False),
        sa.Column("broker_order_id", sa.String, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "positions",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("symbol", sa.String, nullable=False),
        sa.Column("asset_type", sa.String, nullable=False),
        sa.Column("strategy", sa.String, nullable=False),
        sa.Column("quantity", sa.Float, nullable=False),
        sa.Column("entry_price", sa.Float, nullable=False),
        sa.Column("capital_allocated", sa.Float, nullable=False),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("opened_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "portfolio_snapshots",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("portfolio_value", sa.Float, nullable=False),
        sa.Column("open_positions", sa.Integer, nullable=False),
        sa.Column("realized_pnl", sa.Float, nullable=False),
        sa.Column("capital_deployed", sa.Float, nullable=False),
        sa.Column("timestamp", sa.DateTime, nullable=True),
    )

    op.create_table(
        "strategy_configs",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("symbol", sa.String, nullable=False),
        sa.Column("asset_type", sa.String, nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=True),
        sa.Column("params", sa.JSON, nullable=True),
        sa.Column("stop_loss_pct", sa.Float, nullable=True),
        sa.Column("take_profit_pct", sa.Float, nullable=True),
        sa.Column("position_size_pct", sa.Float, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("strategy_configs")
    op.drop_table("portfolio_snapshots")
    op.drop_table("positions")
    op.drop_table("trades")
