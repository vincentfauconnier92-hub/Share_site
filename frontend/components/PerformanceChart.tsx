"use client";

import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, ReferenceLine,
} from "recharts";
import { SnapshotEntry } from "@/lib/api";

function fmt(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" }) +
    " " + d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload as SnapshotEntry;
  const pnl = d.realized_pnl;
  const pnlColor = pnl >= 0 ? "text-emerald-400" : "text-red-400";
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-sm shadow-xl">
      <p className="text-gray-400 mb-2">{fmt(d.timestamp)}</p>
      <p className="text-white font-bold">Valeur : {d.portfolio_value.toFixed(2)}$</p>
      <p className={pnlColor}>P&L réalisé : {pnl >= 0 ? "+" : ""}{pnl.toFixed(2)}$</p>
      <p className="text-gray-400">Positions ouvertes : {d.open_positions}</p>
    </div>
  );
}

interface Props {
  data: SnapshotEntry[];
  initialCapital: number;
}

export default function PerformanceChart({ data, initialCapital }: Props) {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-500 text-sm">
        Aucune donnée encore — le graphique s'alimente à chaque cycle du bot.
      </div>
    );
  }

  const lastValue = data[data.length - 1]?.portfolio_value ?? initialCapital;
  const totalPnl = lastValue - initialCapital;
  const pnlPct = ((totalPnl / initialCapital) * 100).toFixed(2);
  const isPositive = totalPnl >= 0;

  return (
    <div className="space-y-4">
      <div className="flex items-end gap-6">
        <div>
          <p className="text-gray-400 text-xs">Valeur du portefeuille</p>
          <p className="text-2xl font-bold">{lastValue.toFixed(2)}$</p>
        </div>
        <div>
          <p className="text-gray-400 text-xs">P&L total</p>
          <p className={`text-lg font-semibold ${isPositive ? "text-emerald-400" : "text-red-400"}`}>
            {isPositive ? "+" : ""}{totalPnl.toFixed(2)}$ ({isPositive ? "+" : ""}{pnlPct}%)
          </p>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="perfGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={isPositive ? "#10b981" : "#ef4444"} stopOpacity={0.3} />
              <stop offset="95%" stopColor={isPositive ? "#10b981" : "#ef4444"} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis
            dataKey="timestamp"
            tickFormatter={(v) => fmt(v).split(" ")[0]}
            tick={{ fill: "#6b7280", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={["auto", "auto"]}
            tick={{ fill: "#6b7280", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => `${v.toFixed(0)}$`}
            width={60}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine y={initialCapital} stroke="#4b5563" strokeDasharray="4 4" />
          <Area
            type="monotone"
            dataKey="portfolio_value"
            stroke={isPositive ? "#10b981" : "#ef4444"}
            strokeWidth={2}
            fill="url(#perfGrad)"
            dot={false}
            activeDot={{ r: 4, fill: isPositive ? "#10b981" : "#ef4444" }}
          />
        </AreaChart>
      </ResponsiveContainer>
      <p className="text-xs text-gray-600 text-right">Ligne pointillée = capital initial ({initialCapital}$)</p>
    </div>
  );
}
