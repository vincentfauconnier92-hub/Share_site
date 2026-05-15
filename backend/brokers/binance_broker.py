from binance.client import Client
from core.config import settings


class BinanceBroker:
    def __init__(self):
        self.client = Client(
            api_key=settings.BINANCE_API_KEY,
            api_secret=settings.BINANCE_SECRET_KEY,
            testnet=settings.BINANCE_TESTNET,
        )

    def get_account(self) -> dict:
        return self.client.get_account()

    def get_balance(self, asset: str = "USDT") -> float:
        balances = self.client.get_account()["balances"]
        for b in balances:
            if b["asset"] == asset:
                return float(b["free"])
        return 0.0

    def place_order(self, symbol: str, qty: float, side: str) -> dict:
        order_side = Client.SIDE_BUY if side == "buy" else Client.SIDE_SELL
        order = self.client.order_market(
            symbol=symbol.replace("/", ""),
            side=order_side,
            quantity=qty,
        )
        return {"broker_order_id": str(order["orderId"]), "status": order["status"]}

    def get_latest_price(self, symbol: str) -> float:
        ticker = self.client.get_symbol_ticker(symbol=symbol.replace("/", ""))
        return float(ticker["price"])
