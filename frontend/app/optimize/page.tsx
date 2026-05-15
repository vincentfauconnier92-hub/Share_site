"use client";

import { useState } from "react";
import { api, OptimizeRequest, OptimizeResult } from "@/lib/api";

const STRATEGIES = ["MA Crossover", "RSI", "MACD", "Bollinger Bands"];

const PARAM_LABELS: Record<string, Record<string, string>> = {
  "MA Crossover": { short_window: "MA courte", long_window: "MA longue" },
  RSI: { period: "Période", oversold: "Survente", overbought: "Surachat" },
  MACD: { fast: "EMA rapide", slow: "EMA lente", signal_period: "Signal" },
  "Bollinger Bands": { window: "Fenêtre", num_std: "Écart-type" },
};

export default function OptimizePage() {
  const [form, setForm] = useState<OptimizeRequest>({
    symbol: "",
    asset_type: "stock",
    strategy_name: "MA Crossover",
    period: "1an",
    cash: 10_000,
  });
  const [result, setResult] = useState<OptimizeResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activated, setActivated] = useState(false);

  const inputCls = "bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500 w-full";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    setActivated(false);
    try {
      setResult(await api.optimizeStrategy(form));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  };

  const handleActivateBest = async () => {
    if (!result) return;
    await api.activateFromScan(result.symbol, result.strategy, form.asset_type);
    setActivated(true);
  };

  const field = (label: string, node: React.ReactNode) => (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-gray-400">{label}</span>
      {node}
    </label>
  );

  const paramLabels = PARAM_LABELS[form.strategy_name] ?? {};

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold">Optimisation des paramètres</h1>
        <p className="text-gray-400 text-sm mt-1">
          Teste automatiquement toutes les combinaisons de paramètres et trouve la plus performante par Sharpe ratio.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          {field("Stratégie", (
            <select className={inputCls} value={form.strategy_name}
              onChange={(e) => setForm({ ...form, strategy_name: e.target.value })}>
              {STRATEGIES.map((s) => <option key={s}>{s}</option>)}
            </select>
          ))}
          {field("Type d'actif", (
            <select className={inputCls} value={form.asset_type}
              onChange={(e) => setForm({ ...form, asset_type: e.target.value })}>
              <option value="stock">Actions (Nasdaq)</option>
              <option value="crypto">Crypto</option>
            </select>
          ))}
          {field("Symbole (ex: AAPL, NVDA)", (
            <input className={inputCls} value={form.symbol}
              onChange={(e) => setForm({ ...form, symbol: e.target.value })} required />
          ))}
          {field("Période", (
            <select className={inputCls} value={form.period}
              onChange={(e) => setForm({ ...form, period: e.target.value })}>
              <option value="1an">1 an</option>
              <option value="3ans">3 ans</option>
            </select>
          ))}
        </div>

        <p className="text-xs text-gray-500">
          {Object.keys(paramLabels).length > 0 && (
            <>Paramètres testés : {Object.values(paramLabels).join(", ")}</>
          )}
        </p>

        <button type="submit" disabled={loading}
          className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white py-2.5 rounded-lg font-medium transition-colors">
          {loading ? "Optimisation en cours…" : "Lancer l'optimisation"}
        </button>
      </form>

      {error && (
        <div className="bg-red-900/30 border border-red-800 text-red-300 rounded-xl p-4 text-sm">{error}</div>
      )}

      {result && (
        <div className="space-y-4">
          {/* Meilleure combinaison */}
          <div className="bg-emerald-950/40 border border-emerald-800 rounded-xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-emerald-400 font-medium uppercase tracking-wide">Meilleure combinaison</p>
                <h2 className="text-lg font-bold mt-0.5">{result.strategy} · {result.symbol}</h2>
                <p className="text-gray-400 text-sm">{result.combinations_tested} combinaisons testées sur {result.period === "1an" ? "1 an" : "3 ans"}</p>
              </div>
              <button
                onClick={handleActivateBest}
                disabled={activated}
                className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
                  activated ? "bg-gray-800 text-gray-500" : "bg-emerald-600 hover:bg-emerald-500 text-white"
                }`}
              >
                {activated ? "✓ Activé" : "Activer cette config"}
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {Object.entries(result.best.params).map(([k, v]) => (
                <div key={k} className="bg-gray-800 rounded-lg p-3 text-center">
                  <p className="text-gray-400 text-xs">{paramLabels[k] ?? k}</p>
                  <p className="text-white font-bold">{String(v)}</p>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 border-t border-gray-800 pt-4">
              {[
                { label: "Sharpe", value: result.best.sharpe_ratio, color: result.best.sharpe_ratio >= 1 ? "text-emerald-400" : "text-orange-400" },
                { label: "Rendement", value: `${result.best.return_pct >= 0 ? "+" : ""}${result.best.return_pct}%`, color: result.best.return_pct >= 0 ? "text-emerald-400" : "text-red-400" },
                { label: "Drawdown", value: `${result.best.max_drawdown_pct}%`, color: "text-red-400" },
                { label: "Trades", value: result.best.num_trades, color: "text-white" },
                { label: "Réussite", value: `${result.best.win_rate_pct}%`, color: result.best.win_rate_pct >= 50 ? "text-emerald-400" : "text-orange-400" },
              ].map(({ label, value, color }) => (
                <div key={label} className="bg-gray-800 rounded-lg p-3 text-center">
                  <p className="text-gray-400 text-xs">{label}</p>
                  <p className={`font-bold ${color}`}>{value}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Toutes les combinaisons */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-800 text-sm font-medium">
              Toutes les combinaisons ({result.all.length} résultats)
            </div>
            <table className="w-full text-sm">
              <thead className="text-gray-400 border-b border-gray-800">
                <tr>
                  <th className="px-4 py-3 text-left">#</th>
                  {Object.values(paramLabels).map((l) => (
                    <th key={l} className="px-4 py-3 text-left font-medium">{l}</th>
                  ))}
                  <th className="px-4 py-3 text-left font-medium">Sharpe</th>
                  <th className="px-4 py-3 text-left font-medium">Rendement</th>
                  <th className="px-4 py-3 text-left font-medium">Drawdown</th>
                  <th className="px-4 py-3 text-left font-medium">Trades</th>
                </tr>
              </thead>
              <tbody>
                {result.all.map((r, i) => (
                  <tr key={i} className={`border-b border-gray-800 hover:bg-gray-800/40 ${i === 0 ? "bg-emerald-950/20" : ""}`}>
                    <td className="px-4 py-2 text-gray-500">{i + 1}</td>
                    {Object.keys(paramLabels).map((k) => (
                      <td key={k} className="px-4 py-2 font-mono text-xs">{String(r.params[k])}</td>
                    ))}
                    <td className={`px-4 py-2 font-bold ${r.sharpe_ratio >= 1 ? "text-emerald-400" : "text-orange-400"}`}>{r.sharpe_ratio}</td>
                    <td className={`px-4 py-2 ${r.return_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}>{r.return_pct >= 0 ? "+" : ""}{r.return_pct}%</td>
                    <td className="px-4 py-2 text-red-400">{r.max_drawdown_pct}%</td>
                    <td className="px-4 py-2">{r.num_trades}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
