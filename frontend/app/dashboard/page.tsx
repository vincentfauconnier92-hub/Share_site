"use client";

import { useEffect, useState } from "react";
import { api, Trade, PortfolioState, SnapshotEntry, UnrealizedPnlData } from "@/lib/api";
import PerformanceChart from "@/components/PerformanceChart";

function StatCard({ label, value, color = "text-white" }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <p className="text-gray-400 text-sm mb-1">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = pct >= 60 ? "bg-emerald-500" : pct >= 30 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-800 rounded-full h-1.5">
        <div className={`${color} h-1.5 rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-400 w-8">{pct}%</span>
    </div>
  );
}

function statusColor(status: Trade["status"]) {
  return { filled: "text-emerald-400", failed: "text-red-400", pending: "text-yellow-400", cancelled: "text-gray-500" }[status];
}

function PnlValue({ value, suffix = "" }: { value: number | null; suffix?: string }) {
  if (value === null) return <span className="text-gray-500">—</span>;
  const color = value > 0 ? "text-emerald-400" : value < 0 ? "text-red-400" : "text-gray-300";
  const sign = value > 0 ? "+" : "";
  return <span className={color}>{sign}{value.toFixed(2)}{suffix}</span>;
}

export default function DashboardPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [portfolio, setPortfolio] = useState<PortfolioState | null>(null);
  const [history, setHistory] = useState<SnapshotEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [liveData, setLiveData] = useState<UnrealizedPnlData | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  useEffect(() => {
    Promise.all([api.getTrades(), api.getPortfolio(), api.getPortfolioHistory()])
      .then(([t, p, h]) => { setTrades(t); setPortfolio(p); setHistory(h); })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const fetchLive = () => {
      api.getUnrealizedPnl()
        .then((data) => { setLiveData(data); setLastUpdated(new Date()); })
        .catch(() => {});
    };
    fetchLive();
    const interval = setInterval(fetchLive, 10_000);
    return () => clearInterval(interval);
  }, []);

  const filled = trades.filter((t) => t.status === "filled");
  const buys = filled.filter((t) => t.action === "buy").length;
  const sells = filled.filter((t) => t.action === "sell").length;
  const topSignals = portfolio?.signals.filter((s) => s.action === "buy").slice(0, 5) ?? [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* Stats globales */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Positions ouvertes" value={portfolio?.positions.length ?? "—"} color="text-emerald-400" />
        <StatCard label="Trades exécutés" value={filled.length} />
        <StatCard label="Achats" value={buys} color="text-blue-400" />
        <StatCard label="Ventes" value={sells} color="text-orange-400" />
      </div>

      {/* P&L temps réel */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
            <span className="font-medium">P&amp;L temps réel</span>
          </div>
          <span className="text-xs text-gray-500">
            {lastUpdated ? `Mis à jour ${Math.round((Date.now() - lastUpdated.getTime()) / 1000)}s` : "Chargement…"}
          </span>
        </div>

        {/* Métriques clés */}
        <div className="grid grid-cols-3 divide-x divide-gray-800 border-b border-gray-800">
          <div className="px-5 py-4">
            <p className="text-gray-400 text-xs mb-1">P&amp;L latent total</p>
            <p className="text-xl font-bold">
              {liveData ? <PnlValue value={liveData.total_unrealized_pnl} suffix="$" /> : <span className="text-gray-500">—</span>}
            </p>
          </div>
          <div className="px-5 py-4">
            <p className="text-gray-400 text-xs mb-1">P&amp;L réalisé</p>
            <p className="text-xl font-bold">
              {liveData ? <PnlValue value={liveData.realized_pnl} suffix="$" /> : <span className="text-gray-500">—</span>}
            </p>
          </div>
          <div className="px-5 py-4">
            <p className="text-gray-400 text-xs mb-1">Valeur MtM</p>
            <p className="text-xl font-bold text-white">
              {liveData ? `${liveData.mark_to_market_value.toFixed(2)}$` : "—"}
            </p>
          </div>
        </div>

        {/* Tableau par position */}
        {!liveData || liveData.positions.length === 0 ? (
          <p className="px-5 py-4 text-gray-500 text-sm">Aucune position ouverte.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-gray-400 border-b border-gray-800">
              <tr>
                {["Symbole", "Stratégie", "Qté", "Prix entrée", "Prix actuel", "P&L latent", "Retour %"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {liveData.positions.map((pos) => (
                <tr key={pos.id} className="border-b border-gray-800 hover:bg-gray-800/40">
                  <td className="px-4 py-3 font-mono font-medium text-emerald-400">{pos.symbol}</td>
                  <td className="px-4 py-3 text-gray-300">{pos.strategy}</td>
                  <td className="px-4 py-3 text-gray-300">{pos.quantity}</td>
                  <td className="px-4 py-3 text-gray-300">{pos.entry_price.toFixed(2)}$</td>
                  <td className="px-4 py-3">
                    {pos.current_price !== null ? `${pos.current_price.toFixed(2)}$` : <span className="text-gray-500">—</span>}
                  </td>
                  <td className="px-4 py-3 font-medium">
                    <PnlValue value={pos.unrealized_pnl} suffix="$" />
                  </td>
                  <td className="px-4 py-3 font-medium">
                    <PnlValue value={pos.return_pct} suffix="%" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Bandeau stop-loss */}
      {portfolio?.stop_loss_triggered && (
        <div className="bg-red-950 border border-red-700 rounded-xl px-5 py-4 flex items-center gap-3">
          <span className="text-2xl">🛑</span>
          <div>
            <p className="text-red-300 font-bold">Stop-loss global déclenché</p>
            <p className="text-red-400 text-sm">
              Le portefeuille a perdu plus de {portfolio.config.stop_loss_pct}% (seuil : {portfolio.config.stop_loss_threshold}$).
              Toutes les positions ont été fermées. Le bot est en pause.
            </p>
          </div>
        </div>
      )}

      {/* Graphique de performance */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="font-medium mb-4">Performance du portefeuille</h2>
        <PerformanceChart data={history} initialCapital={10000} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Positions actives */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-800 flex items-center justify-between">
            <span className="font-medium">Positions actives</span>
            {portfolio && (
              <span className="text-xs text-gray-500">
                {portfolio.positions.length}/{portfolio.config.top_n} slots · rééquilibrage si +{portfolio.config.rebalance_threshold_pct}%
              </span>
            )}
          </div>
          {loading ? (
            <p className="p-5 text-gray-500">Chargement…</p>
          ) : !portfolio || portfolio.positions.length === 0 ? (
            <p className="p-5 text-gray-500">Aucune position ouverte. Activez des stratégies pour que le bot commence à trader.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-gray-400 border-b border-gray-800">
                <tr>
                  {["Symbole", "Stratégie", "Capital", "Score", "Depuis"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {portfolio.positions.map((p) => (
                  <tr key={p.id} className="border-b border-gray-800 hover:bg-gray-800/40">
                    <td className="px-4 py-3 font-mono font-medium text-emerald-400">{p.symbol}</td>
                    <td className="px-4 py-3 text-gray-300">{p.strategy}</td>
                    <td className="px-4 py-3">{p.capital_allocated.toFixed(0)}€</td>
                    <td className="px-4 py-3 w-32"><ScoreBar score={p.score} /></td>
                    <td className="px-4 py-3 text-gray-400 text-xs">{new Date(p.opened_at).toLocaleDateString("fr-FR")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Meilleurs signaux en cours */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-800">
            <span className="font-medium">Meilleurs signaux d'achat</span>
            <span className="text-gray-500 text-xs ml-2">(mis à jour à chaque cycle)</span>
          </div>
          {loading ? (
            <p className="p-5 text-gray-500">Chargement…</p>
          ) : topSignals.length === 0 ? (
            <p className="p-5 text-gray-500">Aucun signal actif. Ajoutez des stratégies dans l'onglet Stratégies.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-gray-400 border-b border-gray-800">
                <tr>
                  {["Rang", "Symbole", "Stratégie", "Score"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {topSignals.map((s, i) => (
                  <tr key={i} className={`border-b border-gray-800 hover:bg-gray-800/40 ${i < 3 ? "bg-emerald-950/20" : ""}`}>
                    <td className="px-4 py-3 text-gray-500">#{i + 1}{i < 3 && <span className="ml-1 text-emerald-500">●</span>}</td>
                    <td className="px-4 py-3 font-mono font-medium">{s.symbol}</td>
                    <td className="px-4 py-3 text-gray-300">{s.strategy}</td>
                    <td className="px-4 py-3 w-32"><ScoreBar score={s.score} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Derniers trades */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-800 font-medium">Derniers trades</div>
        {loading ? (
          <p className="p-5 text-gray-500">Chargement…</p>
        ) : trades.length === 0 ? (
          <p className="p-5 text-gray-500">Aucun trade enregistré.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-gray-400 border-b border-gray-800">
              <tr>
                {["Symbole", "Action", "Quantité", "Prix", "Stratégie", "Statut", "Date"].map((h) => (
                  <th key={h} className="px-5 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {trades.slice(0, 10).map((t) => (
                <tr key={t.id} className="border-b border-gray-800 hover:bg-gray-800/50">
                  <td className="px-5 py-3 font-mono">{t.symbol}</td>
                  <td className={`px-5 py-3 font-medium ${t.action === "buy" ? "text-emerald-400" : "text-red-400"}`}>
                    {t.action === "buy" ? "Achat" : "Vente"}
                  </td>
                  <td className="px-5 py-3">{t.quantity}</td>
                  <td className="px-5 py-3">{t.price ?? "—"}</td>
                  <td className="px-5 py-3">{t.strategy ?? "—"}</td>
                  <td className={`px-5 py-3 ${statusColor(t.status)}`}>{t.status}</td>
                  <td className="px-5 py-3 text-gray-400">{new Date(t.created_at).toLocaleString("fr-FR")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
