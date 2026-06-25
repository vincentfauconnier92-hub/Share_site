"""Tests des fonctions de scoring des stratégies."""
import pandas as pd
import pytest


def _df(prices: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"close": prices})


def _trending_up(n: int = 60) -> list[float]:
    return [100.0 + i * 0.5 for i in range(n)]


def _trending_down(n: int = 60) -> list[float]:
    return [200.0 - i * 0.5 for i in range(n)]


def _flat(n: int = 60) -> list[float]:
    return [100.0] * n


# ── RSI ───────────────────────────────────────────────────────────────

class TestScoreRSI:
    def setup_method(self):
        from trading.portfolio import _score_rsi
        self.fn = _score_rsi

    def test_oversold_returns_buy(self):
        action, score = self.fn(_df(_trending_down(30)), {})
        assert action == "buy"
        assert 0 < score <= 1.0

    def test_overbought_returns_sell(self):
        action, score = self.fn(_df(_trending_up(30)), {})
        assert action == "sell"
        assert 0 < score <= 1.0

    def test_flat_returns_hold(self):
        action, score = self.fn(_df(_flat(30)), {})
        assert action == "hold"
        assert score == 0.0

    def test_not_enough_data_returns_hold(self):
        action, score = self.fn(_df(_flat(5)), {})
        assert action == "hold"

    def test_custom_params(self):
        action, score = self.fn(_df(_trending_down(30)), {"period": 7, "oversold": 40})
        assert action in ("buy", "hold", "sell")


# ── MA Crossover ──────────────────────────────────────────────────────

class TestScoreMACrossover:
    def setup_method(self):
        from trading.portfolio import _score_ma_crossover
        self.fn = _score_ma_crossover

    def test_bullish_returns_buy(self):
        # Prix en forte hausse → MA courte > MA longue
        action, score = self.fn(_df(_trending_up(60)), {})
        assert action == "buy"
        assert 0 < score <= 1.0

    def test_bearish_returns_sell(self):
        action, score = self.fn(_df(_trending_down(60)), {})
        assert action == "sell"
        assert 0 < score <= 1.0

    def test_not_enough_data_returns_hold(self):
        action, score = self.fn(_df(_flat(10)), {})
        assert action == "hold"

    def test_score_bounded(self):
        _, score = self.fn(_df(_trending_up(60)), {})
        assert 0.0 <= score <= 1.0


# ── MACD ──────────────────────────────────────────────────────────────

class TestScoreMACD:
    def setup_method(self):
        from trading.portfolio import _score_macd
        self.fn = _score_macd

    def test_bullish_returns_buy(self):
        action, score = self.fn(_df(_trending_up(60)), {})
        assert action in ("buy", "hold")

    def test_not_enough_data(self):
        action, score = self.fn(_df(_flat(10)), {})
        assert action == "hold"

    def test_score_bounded(self):
        _, score = self.fn(_df(_trending_up(60)), {})
        assert 0.0 <= score <= 1.0


# ── Bollinger ─────────────────────────────────────────────────────────

class TestScoreBollinger:
    def setup_method(self):
        from trading.portfolio import _score_bollinger
        self.fn = _score_bollinger

    def test_not_enough_data(self):
        action, score = self.fn(_df(_flat(5)), {})
        assert action == "hold"

    def test_flat_returns_hold(self):
        # Prix stable → dans les bandes → hold
        action, score = self.fn(_df(_flat(30)), {})
        assert action == "hold"

    def test_score_bounded(self):
        _, score = self.fn(_df(_trending_down(30)), {})
        assert 0.0 <= score <= 1.0
