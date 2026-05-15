"use client";

import { useEffect, useState } from "react";
import { api, StrategyConfig, StrategyConfigIn } from "@/lib/api";

const STRATEGY_NAMES = ["MA Crossover", "RSI", "MACD", "Bollinger Bands"];
const ASSET_TYPES = ["stock", "crypto"] as const;

const defaultForm: StrategyConfigIn = {
  name: "MA Crossover",
  symbol: "",
  asset_type: "stock",
  enabled: true,
  params: {},
  stop_loss_pct: 5,
  take_profit_pct: 10,
  position_size_pct: 10,
};

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState<StrategyConfig[]>([]);
  const [form, setForm] = useState<StrategyConfigIn>(defaultForm);
  const [editId, setEditId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = () => api.getStrategies().then(setStrategies);
  useEffect(() => { refresh(); }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (editId !== null) {
        await api.updateStrategy(editId, form);
      } else {
        await api.createStrategy(form);
      }
      setForm(defaultForm);
      setEditId(null);
      await refresh();
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (s: StrategyConfig) => {
    setEditId(s.id);
    setForm({ name: s.name, symbol: s.symbol, asset_type: s.asset_type, enabled: s.enabled, params: s.params, stop_loss_pct: s.stop_loss_pct, take_profit_pct: s.take_profit_pct, position_size_pct: s.position_size_pct });
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Supprimer cette stratégie ?")) return;
    await api.deleteStrategy(id);
    await refresh();
  };

  const field = (label: string, node: React.ReactNode) => (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-gray-400">{label}</span>
      {node}
    </label>
  );

  const inputCls = "bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-emerald-500";

  return (
    <div className="space-y-8 max-w-3xl">
      <h1 className="text-2xl font-bold">Stratégies</h1>

      <form onSubmit={handleSubmit} className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
        <h2 className="font-semibold">{editId !== null ? "Modifier la stratégie" : "Nouvelle stratégie"}</h2>

        <div className="grid grid-cols-2 gap-4">
          {field("Stratégie", <select className={inputCls} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}>
            {STRATEGY_NAMES.map((n) => <option key={n}>{n}</option>)}
          </select>)}

          {field("Type d'actif", <select className={inputCls} value={form.asset_type} onChange={(e) => setForm({ ...form, asset_type: e.target.value as "stock" | "crypto" })}>
            {ASSET_TYPES.map((t) => <option key={t}>{t}</option>)}
          </select>)}

          {field("Symbole (ex: AAPL, BTC/USDT)", <input className={inputCls} value={form.symbol} onChange={(e) => setForm({ ...form, symbol: e.target.value })} required />)}

          {field("Stop-loss (%)", <input type="number" className={inputCls} value={form.stop_loss_pct} onChange={(e) => setForm({ ...form, stop_loss_pct: +e.target.value })} min={0} step={0.5} />)}

          {field("Take-profit (%)", <input type="number" className={inputCls} value={form.take_profit_pct} onChange={(e) => setForm({ ...form, take_profit_pct: +e.target.value })} min={0} step={0.5} />)}

          {field("Taille de position (%)", <input type="number" className={inputCls} value={form.position_size_pct} onChange={(e) => setForm({ ...form, position_size_pct: +e.target.value })} min={1} max={100} step={1} />)}
        </div>

        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input type="checkbox" checked={form.enabled} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} className="accent-emerald-500 w-4 h-4" />
          <span className="text-gray-300">Stratégie active (le bot tradéra automatiquement)</span>
        </label>

        <div className="flex gap-3">
          <button type="submit" disabled={loading} className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white px-5 py-2 rounded-lg font-medium transition-colors">
            {loading ? "Enregistrement…" : editId !== null ? "Mettre à jour" : "Ajouter"}
          </button>
          {editId !== null && (
            <button type="button" onClick={() => { setEditId(null); setForm(defaultForm); }} className="border border-gray-700 px-5 py-2 rounded-lg hover:bg-gray-800 transition-colors">
              Annuler
            </button>
          )}
        </div>
      </form>

      <div className="space-y-3">
        {strategies.length === 0 ? (
          <p className="text-gray-500">Aucune stratégie configurée.</p>
        ) : strategies.map((s) => (
          <div key={s.id} className="bg-gray-900 border border-gray-800 rounded-xl px-5 py-4 flex items-center justify-between">
            <div>
              <span className="font-medium">{s.name}</span>
              <span className="ml-3 font-mono text-emerald-400">{s.symbol}</span>
              <span className="ml-2 text-gray-500 text-sm">({s.asset_type})</span>
              <div className="text-sm text-gray-400 mt-1">
                SL {s.stop_loss_pct}% · TP {s.take_profit_pct}% · Position {s.position_size_pct}%
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className={`text-xs px-2 py-1 rounded-full ${s.enabled ? "bg-emerald-900 text-emerald-300" : "bg-gray-800 text-gray-500"}`}>
                {s.enabled ? "Actif" : "Inactif"}
              </span>
              <button onClick={() => handleEdit(s)} className="text-sm text-blue-400 hover:text-blue-300">Modifier</button>
              <button onClick={() => handleDelete(s.id)} className="text-sm text-red-400 hover:text-red-300">Supprimer</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
