/**
 * API client — mock mode by default, switches to real backend via USE_REAL_API env var.
 *
 * Real endpoints (Python backend expected at NEXT_PUBLIC_API_URL):
 *   GET /api/market/regime
 *   GET /api/candidates
 *   GET /api/candidates/:symbol
 *   GET /api/decision-log
 *   GET /api/positions
 *   GET /api/trades
 *   GET /api/performance
 *   GET /api/params
 */

import type {
  MarketRegime,
  SystemHealth,
  Candidate,
  CandidateDetail,
  DecisionEvent,
  Position,
  Trade,
  StrategyPerf,
  RiskMetric,
  Param,
  PeriodPerf,
} from '@/src/types/trading'

import {
  MOCK_CANDIDATES,
  MOCK_POSITIONS,
  MOCK_TRADES,
  MOCK_STRATEGY_PERF,
  MOCK_RISK_METRICS,
  MOCK_FILTER_STATS,
  BASE_DECISION_LOG,
  getMockDetail,
} from '@/src/lib/mock'
import type { FilterStat } from '@/src/types/trading'

const USE_MOCK = process.env.NEXT_PUBLIC_USE_REAL_API !== 'true'
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, { cache: 'no-store' })
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`)
  return res.json() as Promise<T>
}

// ─── Market ───────────────────────────────────────────────────────────────────

export interface MarketState {
  regime: MarketRegime
  health: SystemHealth
}

const MOCK_MARKET: MarketState = {
  regime: {
    regime: 'TREND',
    score: 78,
    vix: 18.4,
    adx: 32.1,
    trend: 80,
    momentum: 71,
    volume: 55,
    risk: 38,
  },
  health: {
    dataFeed:    { status: 'ok',   latency: 3  },
    orderRouter: { status: 'ok',   latency: 12 },
    riskEngine:  { status: 'ok',   latency: 1  },
    signalGen:   { status: 'warn', latency: 45 },
  },
}

export async function fetchMarket(): Promise<MarketState> {
  if (USE_MOCK) return MOCK_MARKET
  return get<MarketState>('/api/market/regime')
}

// ─── Candidates ───────────────────────────────────────────────────────────────

export async function fetchCandidates(): Promise<Candidate[]> {
  if (USE_MOCK) return MOCK_CANDIDATES
  return get<Candidate[]>('/api/candidates')
}

export async function fetchCandidateDetail(symbol: string): Promise<CandidateDetail> {
  if (USE_MOCK) return getMockDetail(symbol)
  return get<CandidateDetail>(`/api/candidates/${symbol}`)
}

// ─── Decision Log ─────────────────────────────────────────────────────────────

export async function fetchDecisionLog(): Promise<DecisionEvent[]> {
  if (USE_MOCK) return BASE_DECISION_LOG
  return get<DecisionEvent[]>('/api/decision-log')
}

// ─── Positions & Trades ───────────────────────────────────────────────────────

export async function fetchPositions(): Promise<Position[]> {
  if (USE_MOCK) return MOCK_POSITIONS
  return get<Position[]>('/api/positions')
}

interface TradesResponse {
  period: { days: number; from: string; to: string; label: string }
  total:  number
  trades: Trade[]
}

export async function fetchTrades(
  range: { from: string; to: string } | { days: number } = { days: 7 }
): Promise<{ trades: Trade[]; period: TradesResponse['period'] | null }> {
  if (USE_MOCK) return { trades: MOCK_TRADES, period: null }
  const qs = 'from' in range
    ? `from_date=${range.from}&to_date=${range.to}&limit=100`
    : `days=${range.days}&limit=100`
  const res = await get<TradesResponse | Trade[]>(`/api/trades?${qs}`)
  if (Array.isArray(res)) return { trades: res, period: null }
  const r = res as TradesResponse
  return { trades: r.trades ?? [], period: r.period ?? null }
}

// ─── Performance ─────────────────────────────────────────────────────────────

export interface PerformanceState {
  today: PeriodPerf
  week: PeriodPerf
  month: PeriodPerf
  strategies: StrategyPerf[]
  riskMetrics: RiskMetric[]
}

const MOCK_PERFORMANCE: PerformanceState = {
  today:   { pnl: 486310,  pct: 1.87, trades: 5,  winRate: 80 },
  week:    { pnl: 2341000, pct: 4.21, trades: 22, winRate: 72 },
  month:   { pnl: 8942000, pct: 12.8, trades: 89, winRate: 68 },
  strategies: MOCK_STRATEGY_PERF,
  riskMetrics: MOCK_RISK_METRICS,
}

export async function fetchPerformance(): Promise<PerformanceState> {
  if (USE_MOCK) return MOCK_PERFORMANCE
  return get<PerformanceState>('/api/performance')
}

// ─── Params ──────────────────────────────────────────────────────────────────

const MOCK_PARAMS: Param[] = [
  {
    key: 'ema_fast', label: 'EMA Fast', value: 9, defaultValue: 9,
    type: 'number', min: 3, max: 30, step: 1,
    description: 'Fast EMA period for signal generation',
  },
  {
    key: 'ema_slow', label: 'EMA Slow', value: 60, defaultValue: 60,
    type: 'number', min: 20, max: 200, step: 5,
    description: 'Slow EMA period for trend filter',
  },
  {
    key: 'rsi_period', label: 'RSI Period', value: 14, defaultValue: 14,
    type: 'number', min: 5, max: 30, step: 1,
    description: 'RSI calculation period',
  },
  {
    key: 'vol_threshold', label: 'Vol Threshold', value: 1.5, defaultValue: 1.5,
    type: 'number', min: 1.0, max: 5.0, step: 0.1,
    description: 'Minimum volume ratio vs 20MA',
  },
  {
    key: 'atr_mult', label: 'ATR Multiplier', value: 1.5, defaultValue: 1.5,
    type: 'number', min: 0.5, max: 3.0, step: 0.1,
    description: 'ATR multiplier for stop-loss calculation',
  },
  {
    key: 'smc_cutoff', label: 'SMC Cutoff', value: '12:30', defaultValue: '12:30',
    type: 'select', options: ['10:30', '11:00', '11:30', '12:00', '12:30', '13:00'],
    description: 'Latest time for SMC A-grade entry',
  },
  {
    key: 'choch_min_grade', label: 'Min CHoCH Grade', value: 'B', defaultValue: 'B',
    type: 'select', options: ['A', 'B', 'C'],
    description: 'Minimum CHoCH grade required for entry',
  },
  {
    key: 'market_context_enabled', label: 'Market Context', value: true, defaultValue: true,
    type: 'boolean',
    description: 'Enable market-wide context pre-filter',
  },
]

// ─── Filter Stats ─────────────────────────────────────────────────────────────

export async function fetchFilterStats(): Promise<FilterStat[]> {
  if (USE_MOCK) return MOCK_FILTER_STATS
  return get<FilterStat[]>('/api/filter-stats')
}

export async function fetchParams(): Promise<Param[]> {
  if (USE_MOCK) return MOCK_PARAMS
  return get<Param[]>('/api/params')
}

export async function patchParam(key: string, value: Param['value']): Promise<void> {
  if (USE_MOCK) return
  const res = await fetch(`${BASE_URL}/api/params/${key}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ value }),
  })
  if (!res.ok) throw new Error(`PATCH /api/params/${key} → ${res.status}`)
}

export interface AccountState {
  deposit: number
  holdingValue: number
  totalAssets: number
  dailyPnl: number
  weeklyPnl: number
  consecutiveLosses: number
  dataSource?: 'kiwoom_api' | 'estimate'
  snapshotAge?: number | null
}

const MOCK_ACCOUNT: AccountState = {
  deposit: 312_000,
  holdingValue: 43_000,
  totalAssets: 355_000,
  dailyPnl: 250,
  weeklyPnl: -1250,
  consecutiveLosses: 0,
}

export async function fetchAccount(): Promise<AccountState> {
  if (USE_MOCK) return MOCK_ACCOUNT
  return get<AccountState>('/api/account')
}

// ─── Optimize (Grid Search) ───────────────────────────────────────────────────

export interface OptimizeRequest {
  strategy:          string
  start:             string
  end:               string
  mode?:             'tp_sl' | 'swing'
  tp_range:          number[]
  sl_range:          number[]
  min_hold_range?:   number[]
  trailing_range?:   number[]
  be_trigger_range?: number[]
  symbols?:          string[] | null
}

export interface OptimizeStatus {
  job_id:       string
  status:       'queued' | 'running' | 'done' | 'error'
  progress:     number
  total:        number
  message:      string
  error:        string | null
  result_count: number
  // tp_sl 모드 전용 (하위 호환)
  current_tp?:  number | null
  current_sl?:  number | null
}

export interface OptimizeRow {
  rank:          number
  // tp_sl 모드
  tp?:           number
  sl?:           number
  // swing 모드
  min_hold?:     number
  trailing?:     number
  be_trigger?:   number
  trades:        number
  win_pct:       number
  rr:            number
  mdd:           number
  ret:           number
  score:         number
  passed:        string
  // 스윙 — 수익 구조
  capture_rate?:      number   // MFE 포착률 (%)
  avg_mfe_pct?:       number   // 평균 MFE (%)
  big_winner_ratio?:  number   // 실현 수익 10%+ 거래 비율 (%)
  mfe_10plus_ratio?:  number   // MFE 10%+ 도달 비율 — 잠재력 (%)
  // 스윙 — 손실 구조 (MAE)
  avg_mae_pct?:       number   // 평균 MAE (%)
  mae_3plus_ratio?:   number   // MAE > 3% 거래 비율 (%)
  sl_hit_ratio?:      number   // SL/BE_STOP 청산 비율 (%)
  // 스윙 — 시간대별 수익 (일봉 기준)
  ret_d1?:            number   // hold=1봉 평균 pnl%
  ret_d2_5?:          number   // hold 2~5봉 평균 pnl%
  ret_d6_14?:         number   // hold 6~14봉 평균 pnl%
  ret_d15plus?:       number   // hold 15봉+ 평균 pnl% (진짜 스윙)
  cnt_d1?:            number
  cnt_d2_5?:          number
  cnt_d6_14?:         number
  cnt_d15plus?:       number
}

export interface OptimizeResults {
  job_id:   string
  status:   string
  strategy: string
  period:   string
  results:  OptimizeRow[]
  best:     OptimizeRow | null
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    cache: 'no-store',
  })
  if (!res.ok) throw new Error(`POST ${path} → ${res.status}`)
  return res.json() as Promise<T>
}

export async function startOptimize(req: OptimizeRequest): Promise<{ job_id: string }> {
  return post('/api/optimize/run', req)
}

export async function getOptimizeStatus(jobId: string): Promise<OptimizeStatus> {
  return get<OptimizeStatus>(`/api/optimize/status/${jobId}`)
}

export async function getOptimizeResults(jobId: string): Promise<OptimizeResults> {
  return get<OptimizeResults>(`/api/optimize/results/${jobId}`)
}

export async function cancelOptimize(jobId: string): Promise<void> {
  await fetch(`${BASE_URL}/api/optimize/jobs/${jobId}`, { method: 'DELETE' })
}

export async function applyOptimize(tp: number, sl: number): Promise<void> {
  if (USE_MOCK) return
  const res = await fetch(`${BASE_URL}/api/optimize/apply`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tp, sl }),
  })
  if (!res.ok) throw new Error(`Apply failed: ${res.status}`)
}
