"""Tests de validation des modèles Pydantic de l'API."""
import pytest
from pydantic import ValidationError


def _strategy(**kwargs):
    from api.routes import StrategyConfigIn
    return StrategyConfigIn(**{"name": "RSI", "symbol": "AAPL", "asset_type": "stock", **kwargs})


def _backtest(**kwargs):
    from api.routes import BacktestRequest
    return BacktestRequest(**{
        "symbol": "AAPL", "asset_type": "stock", "strategy_name": "RSI",
        "start_date": "2023-01-01", "end_date": "2024-01-01",
        **kwargs,
    })


# ── StrategyConfigIn ──────────────────────────────────────────────────

class TestStrategyConfigIn:
    def test_valid_strategy(self):
        s = _strategy()
        assert s.symbol == "AAPL"
        assert s.name == "RSI"

    def test_symbol_normalized_to_uppercase(self):
        s = _strategy(symbol="aapl")
        assert s.symbol == "AAPL"

    def test_invalid_strategy_name(self):
        with pytest.raises(ValidationError):
            _strategy(name="Unknown Strategy")

    def test_invalid_asset_type(self):
        with pytest.raises(ValidationError):
            _strategy(asset_type="forex")

    def test_symbol_with_spaces(self):
        with pytest.raises(ValidationError):
            _strategy(symbol="AA PL")

    def test_symbol_too_long(self):
        with pytest.raises(ValidationError):
            _strategy(symbol="ABCDEFGHIJKLMNOP")  # 16 chars > 15

    def test_stop_loss_too_low(self):
        with pytest.raises(ValidationError):
            _strategy(stop_loss_pct=0.0)

    def test_stop_loss_too_high(self):
        with pytest.raises(ValidationError):
            _strategy(stop_loss_pct=51.0)

    def test_take_profit_bounds(self):
        with pytest.raises(ValidationError):
            _strategy(take_profit_pct=101.0)

    def test_position_size_bounds(self):
        with pytest.raises(ValidationError):
            _strategy(position_size_pct=11.0)

    def test_valid_rsi_params(self):
        s = _strategy(params={"period": 14, "oversold": 30, "overbought": 70})
        assert s.params["period"] == 14

    def test_unknown_param_key(self):
        with pytest.raises(ValidationError):
            _strategy(params={"unknown_key": 5})

    def test_negative_param_value(self):
        with pytest.raises(ValidationError):
            _strategy(params={"period": -1})


# ── BacktestRequest ───────────────────────────────────────────────────

class TestBacktestRequest:
    def test_valid_request(self):
        b = _backtest()
        assert b.symbol == "AAPL"

    def test_invalid_strategy(self):
        with pytest.raises(ValidationError):
            _backtest(strategy_name="Inexistante")

    def test_start_after_end(self):
        with pytest.raises(ValidationError):
            _backtest(start_date="2024-06-01", end_date="2023-01-01")

    def test_end_in_future(self):
        with pytest.raises(ValidationError):
            _backtest(end_date="2099-12-31")

    def test_before_1990(self):
        with pytest.raises(ValidationError):
            _backtest(start_date="1985-01-01", end_date="1986-01-01")

    def test_period_over_10_years(self):
        with pytest.raises(ValidationError):
            _backtest(start_date="2000-01-01", end_date="2015-01-01")

    def test_invalid_date_format(self):
        with pytest.raises(ValidationError):
            _backtest(start_date="01/01/2023")

    def test_invalid_asset_type(self):
        with pytest.raises(ValidationError):
            _backtest(asset_type="nft")

    def test_cash_must_be_positive(self):
        with pytest.raises(ValidationError):
            _backtest(cash=-100)
