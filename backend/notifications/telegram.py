import hashlib
import logging

import httpx

from core.config import settings

_log = logging.getLogger("trading.telegram")


def _send(text: str) -> None:
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        return
    try:
        httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=5,
        )
    except Exception:
        pass


def alert_trade_open(symbol: str, strategy: str, quantity: float, price: float, score: float) -> None:
    _send(
        f"🟢 <b>ACHAT</b> — {symbol}\n"
        f"Stratégie : {strategy}\n"
        f"Quantité : {quantity:.4f} @ {price:.2f}$\n"
        f"Score signal : {round(score * 100)}%"
    )


def alert_trade_close(symbol: str, strategy: str, quantity: float, price: float, pnl: float) -> None:
    emoji = "🔴" if pnl < 0 else "💰"
    sign = "+" if pnl >= 0 else ""
    _send(
        f"{emoji} <b>VENTE</b> — {symbol}\n"
        f"Stratégie : {strategy}\n"
        f"Quantité : {quantity:.4f} @ {price:.2f}$\n"
        f"P&L : <b>{sign}{pnl:.2f}$</b>"
    )


def alert_rebalance(sold: str, bought: str, reason: str) -> None:
    _send(
        f"🔄 <b>RÉÉQUILIBRAGE</b>\n"
        f"Vendu : {sold}\n"
        f"Acheté : {bought}\n"
        f"Raison : {reason}"
    )


def alert_market_closed() -> None:
    _send("🔔 <b>Marché fermé</b> — le bot est en veille jusqu'à l'ouverture du Nasdaq (15h30 heure de Paris).")


def alert_global_stop_loss(portfolio_value: float, threshold: float, pct: float) -> None:
    _send(
        f"🛑 <b>STOP-LOSS GLOBAL DÉCLENCHÉ</b>\n"
        f"Valeur portefeuille : <b>{portfolio_value:.2f}$</b>\n"
        f"Seuil : {threshold:.2f}$ (-{pct:.0f}%)\n"
        f"Toutes les positions ont été fermées.\n"
        f"Le bot est en pause jusqu'à récupération du capital."
    )


def alert_individual_exit(symbol: str, strategy: str, quantity: float, price: float, pnl: float, reason: str) -> None:
    label = "STOP-LOSS" if reason == "stop_loss" else "TAKE-PROFIT"
    emoji = "🛑" if reason == "stop_loss" else "🎯"
    sign = "+" if pnl >= 0 else ""
    _send(
        f"{emoji} <b>{label}</b> — {symbol}\n"
        f"Stratégie : {strategy}\n"
        f"Quantité : {quantity:.4f} @ {price:.2f}$\n"
        f"P&L : <b>{sign}{pnl:.2f}$</b>"
    )


def alert_error(symbol: str, action: str, error: str) -> None:
    # Le détail complet est enregistré dans les logs locaux uniquement.
    # Telegram ne reçoit qu'un identifiant de référence pour éviter d'exposer
    # des informations sensibles (chemins, stack traces, clés partielles).
    error_ref = hashlib.sha256(error.encode()).hexdigest()[:10]
    _log.error("trading.error symbol=%s action=%s ref=%s detail=%s", symbol, action, error_ref, error)
    _send(
        f"⚠️ <b>Erreur</b> sur {symbol}\n"
        f"Action : {action}\n"
        f"Référence : <code>{error_ref}</code>\n"
        f"Consultez les logs pour le détail."
    )
