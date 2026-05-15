"use client";

import { useState } from "react";
import { api, BacktestRequest, BacktestResult } from "@/lib/api";

const STRATEGY_NAMES = ["MA Crossover", "RSI", "MACD", "Bollinger Bands"];

const defaultForm: BacktestRequest = {
  symbol: "",
  asset_type: "stock",
  strategy_name: "MA Crossover",
  start_date: "2022-01-01",
  end_date: "2024-12-31",
  cash: 10000,
};

function ResultCard({ label, value, color = "text-white" }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="bg-gray-800 rounded-xl p-4 text-center">
      <p className="text-gray-400 text-xs mb-1">{label}</p>
      <p className={`text-xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

export default function BacktestPage() {
  const [form, setForm] = useState<BacktestRequest>(defaultForm);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const inputCls = "bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-emerald-500 w-full";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.runBacktest(form);
      setResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  };

  const field = (label: string, node: React.ReactNode) => (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-gray-400">{label}</span>
      {node}
    </label>
  );

  return (
    <div className="space-y-8 max-w-2xl">
      <h1 className="text-2xl font-bold">Backtesting</h1>

      <form onSubmit={handleSubmit} className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          {field("Stratégie", <select className={inputCls} value={form.strategy_name} onChange={(e) => setForm({ ...form, strategy_name: e.target.value })}>
            {STRATEGY_NAMES.map((n) => <option key={n}>{n}</option>)}
          </select>)}

          {field("Type d'actif", <select className={inputCls} value={form.asset_type} onChange={(e) => setForm({ ...form, asset_type: e.target.value as "stock" | "crypto" })}>
            <option value="stock">Actions (stock)</option>
            <option value="crypto">Crypto</option>
          </select>)}

          {field("Symbole (ex: AAPL, BTC-USD)", <input className={inputCls} value={form.symbol} onChange={(e) => setForm({ ...form, symbol: e.target.value })} required />)}

          {field("Capital initial (€/$)", <input type="number" className={inputCls} value={form.cash} onChange={(e) => setForm({ ...form, cash: +e.target.value })} min={100} />)}

          {field("Date de début", <input type="date" className={inputCls} value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} />)}

          {field("Date de fin", <input type="date" className={inputCls} value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} />)}
        </div>

        <button type="submit" disabled={loading} className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white py-2 rounded-lg font-medium transition-colors">
          {loading ? "Simulation en cours…" : "Lancer le backtest"}
        </button>
      </form>

      {error && (
        <div className="bg-red-900/30 border border-red-800 text-red-300 rounded-xl p-4 text-sm">{error}</div>
      )}

      {result && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
          <h2 className="font-semibold">
            Résultats — {result.strategy} sur {result.symbol}
          </h2>
          <p className="text-gray-400 text-sm">{result.start} → {result.end}</p>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <ResultCard label="Rendement" value={`${result.return_pct}%`} color={result.return_pct >= 0 ? "text-emerald-400" : "text-red-400"} />
            <ResultCard label="Drawdown max" value={`${result.max_drawdown_pct}%`} color="text-red-400" />
            <ResultCard label="Nb trades" value={result.num_trades} />
            <ResultCard label="Taux de réussite" value={`${result.win_rate_pct}%`} color={result.win_rate_pct >= 50 ? "text-emerald-400" : "text-orange-400"} />
            <ResultCard label="Sharpe Ratio" value={result.sharpe_ratio} color={result.sharpe_ratio >= 1 ? "text-emerald-400" : "text-orange-400"} />
          </div>
        </div>
      )}
    </div>
  );
}
