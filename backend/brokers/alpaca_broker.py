from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from core.config import settings


class AlpacaBroker:
    def __init__(self):
        self.client = TradingClient(
            api_key=settings.ALPACA_API_KEY,
            secret_key=settings.ALPACA_SECRET_KEY,
            paper=True,
        )

    def get_account(self):
        return self.client.get_account()

    def get_positions(self):
        return self.client.get_all_positions()

    def place_order(self, symbol: str, qty: float, side: str) -> dict:
        order_side = OrderSide.BUY if side == "buy" else OrderSide.SELL
        request = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=order_side,
            time_in_force=TimeInForce.DAY,
        )
        order = self.client.submit_order(request)
        return {"broker_order_id": str(order.id), "status": str(order.status)}

    def get_latest_price(self, symbol: str) -> float:
        return self.get_latest_prices_batch([symbol])[symbol]

    def get_latest_prices_batch(self, symbols: list[str]) -> dict[str, float]:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockLatestQuoteRequest

        data_client = StockHistoricalDataClient(
            settings.ALPACA_API_KEY, settings.ALPACA_SECRET_KEY
        )
        quotes = data_client.get_stock_latest_quote(
            StockLatestQuoteRequest(symbol_or_symbols=symbols)
        )
        return {s: float(quotes[s].ask_price) for s in symbols}
