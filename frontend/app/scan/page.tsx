"use client";

import { useEffect, useState } from "react";
import { api, ScanResult } from "@/lib/api";

function badge(value: number, thresholds: [number, number], labels = ["text-emerald-400", "text-orange-400", "text-red-400"]) {
  if (value >= thresholds[0]) return labels[0];
  if (value >= thresholds[1]) return labels[1];
  return labels[2];
}

function SharpeBadge({ value }: { value: number }) {
  const color = value >= 1 ? "bg-emerald-900 text-emerald-300" : value >= 0.5 ? "bg-yellow-900 text-yellow-300" : "bg-red-900 text-red-300";
  const label = value >= 1 ? "Excellent" : value >= 0.5 ? "Correct" : "Faible";
  return <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${color}`}>{label}</span>;
}

function estimateDuration(nSymbols: number, nPeriods: number) {
  const total = nSymbols * 2 * nPeriods;
  const seconds = total * 1.5;
  if (seconds < 60) return `~${Math.round(seconds)} secondes`;
  return `~${Math.round(seconds / 60)} minutes`;
}

export default function ScanPage() {
  const [allSymbols, setAllSymbols] = useState<string[]>([]);
  const [symbols, setSymbols] = useState<string[]>([]);
  const [newSymbol, setNewSymbol] = useState("");
  const [periods, setPeriods] = useState<string[]>(["1an", "3ans"]);
  const [results, setResults] = useState<ScanResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [activated, setActivated] = useState<Set<string>>(new Set());
  const [activating, setActivating] = useState<string | null>(null);

  useEffect(() => {
    api.getNasdaq100().then((data) => {
      setAllSymbols(data.symbols);
      setSymbols(data.symbols);
    });
  }, []);

  const togglePeriod = (p: string) =>
    setPeriods((prev) => prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]);

  const addSymbol = () => {
    const s = newSymbol.trim().toUpperCase();
    if (s && !symbols.includes(s)) setSymbols([...symbols, s]);
    setNewSymbol("");
  };

  const handleActivate = async (r: ScanResult) => {
    const key = `${r.symbol}|${r.strategy}`;
    setActivating(key);
    try {
      await api.activateFromScan(r.symbol, r.strategy, "stock");
      setActivated((prev) => new Set([...prev, key]));
    } finally {
      setActivating(null);
    }
  };

  const handleScan = async () => {
    setLoading(true);
    setDone(false);
    setResults([]);
    try {
      const data = await api.runScan({ symbols, periods, cash: 10_000 });
      setResults(data);
      setDone(true);
    } finally {
      setLoading(false);
    }
  };

  const inputCls = "bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Scanner Nasdaq-100</h1>
        <p className="text-gray-400 text-sm mt-1">
          Teste toutes les combinaisons Nasdaq-100 × stratégie × période et classe par Sharpe ratio.
        </p>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-5">

        {/* Périodes */}
        <div>
          <p className="text-sm text-gray-400 mb-2">Périodes</p>
          <div className="flex gap-3">
            {[["1an", "1 an"], ["3ans", "3 ans"]].map(([key, label]) => (
              <button
                key={key}
                onClick={() => togglePeriod(key)}
                className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${
                  periods.includes(key)
                    ? "bg-emerald-700 border-emerald-600 text-white"
                    : "border-gray-700 text-gray-400 hover:border-gray-500"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Sélection des symboles */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-400">
              Actifs sélectionnés <span className="text-white font-medium">{symbols.length}</span> / {allSymbols.length}
            </p>
            <div className="flex gap-2 text-xs">
              <button onClick={() => setSymbols(allSymbols)} className="text-emerald-400 hover:text-emerald-300">Tout sélectionner</button>
              <span className="text-gray-600">·</span>
              <button onClick={() => setSymbols([])} className="text-red-400 hover:text-red-300">Tout désélectionner</button>
            </div>
          </div>

          <div className="max-h-40 overflow-y-auto flex flex-wrap gap-1.5 p-3 bg-gray-800 rounded-lg border border-gray-700 mb-3">
            {allSymbols.map((s) => {
              const active = symbols.includes(s);
              return (
                <button
                  key={s}
                  onClick={() => setSymbols(active ? symbols.filter((x) => x !== s) : [...symbols, s])}
                  className={`px-2 py-0.5 rounded text-xs font-mono transition-colors ${
                    active ? "bg-emerald-700 text-white" : "bg-gray-700 text-gray-400 hover:bg-gray-600"
                  }`}
                >
                  {s}
                </button>
              );
            })}
          </div>

          <div className="flex gap-2">
            <input
              className={inputCls}
              placeholder="Ajouter un symbole hors Nasdaq-100 (ex: HOOD)"
              value={newSymbol}
              onChange={(e) => setNewSymbol(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && addSymbol()}
            />
            <button onClick={addSymbol} className="border border-gray-700 px-4 rounded-lg text-sm hover:bg-gray-800 transition-colors">
              Ajouter
            </button>
          </div>
        </div>

        {symbols.length > 0 && periods.length > 0 && (
          <p className="text-xs text-gray-500">
            {symbols.length * 2 * periods.length} backtests à lancer · durée estimée {estimateDuration(symbols.length, periods.length)}
          </p>
        )}

        <button
          onClick={handleScan}
          disabled={loading || periods.length === 0 || symbols.length === 0}
          className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white py-2.5 rounded-lg font-medium transition-colors"
        >
          {loading
            ? `Analyse en cours… (${symbols.length} actifs × 2 stratégies × ${periods.length} période${periods.length > 1 ? "s" : ""})`
            : `Lancer le scanner (${symbols.length} actifs)`}
        </button>
      </div>

      {/* Résultats */}
      {done && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-800">
            <span className="font-medium">{results.length} combinaisons rentables trouvées</span>
            <span className="text-gray-400 text-sm font-normal ml-2">— classées par Sharpe ratio</span>
          </div>

          {results.length === 0 ? (
            <p className="p-5 text-gray-500">Aucune combinaison avec des trades générés sur cette période.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-gray-400 border-b border-gray-800">
                <tr>
                  {["#", "Actif", "Stratégie", "Période", "Sharpe", "Qualité", "Rendement", "Drawdown max", "Trades", "Réussite", ""].map((h) => (
                    <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {results.map((r, i) => (
                  <tr key={i} className={`border-b border-gray-800 hover:bg-gray-800/40 ${i === 0 ? "bg-emerald-950/30" : ""}`}>
                    <td className="px-4 py-3 text-gray-500">{i + 1}</td>
                    <td className="px-4 py-3 font-mono font-medium">{r.symbol}</td>
                    <td className="px-4 py-3">{r.strategy}</td>
                    <td className="px-4 py-3 text-gray-400">{r.period_label}</td>
                    <td className="px-4 py-3 font-bold">{r.sharpe_ratio}</td>
                    <td className="px-4 py-3"><SharpeBadge value={r.sharpe_ratio} /></td>
                    <td className={`px-4 py-3 font-medium ${badge(r.return_pct, [10, 0])}`}>
                      {r.return_pct >= 0 ? "+" : ""}{r.return_pct}%
                    </td>
                    <td className="px-4 py-3 text-red-400">{r.max_drawdown_pct}%</td>
                    <td className="px-4 py-3">{r.num_trades}</td>
                    <td className={`px-4 py-3 ${badge(r.win_rate_pct, [55, 45])}`}>{r.win_rate_pct}%</td>
                    <td className="px-4 py-3">
                      {(() => {
                        const key = `${r.symbol}|${r.strategy}`;
                        const isActivated = activated.has(key);
                        const isActivating = activating === key;
                        return (
                          <button
                            onClick={() => handleActivate(r)}
                            disabled={isActivated || isActivating !== false}
                            className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
                              isActivated
                                ? "bg-gray-800 text-gray-500 cursor-default"
                                : "bg-emerald-700 hover:bg-emerald-600 text-white disabled:opacity-50"
                            }`}
                          >
                            {isActivated ? "✓ Activé" : isActivating ? "…" : "Activer"}
                          </button>
                        );
                      })()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
