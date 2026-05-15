const BASE = "/api/proxy";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
  });
  if (!res.ok) {
    let detail = "Erreur inconnue";
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {}
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  getTrades: () => request<Trade[]>("/trades"),
  getStrategies: () => request<StrategyConfig[]>("/strategies"),
  createStrategy: (body: StrategyConfigIn) =>
    request<StrategyConfig>("/strategies", { method: "POST", body: JSON.stringify(body) }),
  updateStrategy: (id: number, body: StrategyConfigIn) =>
    request<StrategyConfig>(`/strategies/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteStrategy: (id: number) =>
    request<{ ok: boolean }>(`/strategies/${id}`, { method: "DELETE" }),
  runBacktest: (body: BacktestRequest) =>
    request<BacktestResult>("/backtest", { method: "POST", body: JSON.stringify(body) }),
  runScan: (body: ScanRequest) =>
    request<ScanResult[]>("/backtest/scan", { method: "POST", body: JSON.stringify(body) }),
  activateFromScan: (symbol: string, strategy_name: string, asset_type: string) =>
    request<StrategyConfig>("/strategies/activate-from-scan", {
      method: "POST",
      body: JSON.stringify({ symbol, strategy_name, asset_type }),
    }),
  getPortfolio: () => request<PortfolioState>("/portfolio"),
  getNasdaq100: () => request<{ symbols: string[]; count: number }>("/backtest/scan/nasdaq100"),
  getPortfolioHistory: (limit?: number) =>
    request<SnapshotEntry[]>(`/portfolio/history${limit ? `?limit=${limit}` : ""}`),
  getUnrealizedPnl: () => request<UnrealizedPnlData>("/portfolio/unrealized"),
  optimizeStrategy: (body: OptimizeRequest) =>
    request<OptimizeResult>("/backtest/optimize", { method: "POST", body: JSON.stringify(body) }),
};

export interface Trade {
  id: number;
  symbol: string;
  asset_type: "stock" | "crypto";
  action: "buy" | "sell";
  quantity: number;
  price: number | null;
  status: "pending" | "filled" | "cancelled" | "failed";
  strategy: string | null;
  created_at: string;
}

export interface StrategyConfig {
  id: number;
  name: string;
  symbol: string;
  asset_type: "stock" | "crypto";
  enabled: boolean;
  params: Record<string, unknown>;
  stop_loss_pct: number;
  take_profit_pct: number;
  position_size_pct: number;
}

export type StrategyConfigIn = Omit<StrategyConfig, "id">;

export interface BacktestRequest {
  symbol: string;
  asset_type: "stock" | "crypto";
  strategy_name: string;
  start_date: string;
  end_date: string;
  params?: Record<string, unknown>;
  cash?: number;
}

export interface BacktestResult {
  return_pct: number;
  max_drawdown_pct: number;
  num_trades: number;
  win_rate_pct: number;
  sharpe_ratio: number;
  start: string;
  end: string;
  symbol: string;
  strategy: string;
}

export interface ScanRequest {
  symbols: string[];
  periods: string[];
  cash?: number;
}

export type ScanResult = BacktestResult & { period_label: string };

export interface PortfolioPosition {
  id: number;
  symbol: string;
  asset_type: string;
  strategy: string;
  quantity: number;
  entry_price: number;
  capital_allocated: number;
  score: number;
  opened_at: string;
}

export interface SignalEntry {
  symbol: string;
  strategy: string;
  asset_type: string;
  action: "buy" | "sell" | "hold";
  score: number;
}

export interface OptimizeRequest {
  symbol: string;
  asset_type: string;
  strategy_name: string;
  period: string;
  cash?: number;
}

export interface OptimizeResult {
  best: BacktestResult & { params: Record<string, unknown> };
  all: (BacktestResult & { params: Record<string, unknown> })[];
  symbol: string;
  strategy: string;
  period: string;
  combinations_tested: number;
}

export interface SnapshotEntry {
  timestamp: string;
  portfolio_value: number;
  open_positions: number;
  realized_pnl: number;
  capital_deployed: number;
}

export interface UnrealizedPosition {
  id: number;
  symbol: string;
  asset_type: string;
  strategy: string;
  quantity: number;
  entry_price: number;
  current_price: number | null;
  unrealized_pnl: number | null;
  return_pct: number | null;
  capital_allocated: number;
  opened_at: string;
}

export interface UnrealizedPnlData {
  positions: UnrealizedPosition[];
  total_unrealized_pnl: number;
  realized_pnl: number;
  mark_to_market_value: number;
  updated_at: string;
}

export interface PortfolioState {
  positions: PortfolioPosition[];
  signals: SignalEntry[];
  config: {
    max_positions: number;
    top_n: number;
    rebalance_threshold_pct: number;
    stop_loss_pct: number;
    stop_loss_threshold: number;
  };
  stop_loss_triggered: boolean;
  portfolio_value: number;
}
