// ─── Domain Types ────────────────────────────────────────────────────────────

export type SystemStatus = 'ACTIVE' | 'STOPPED' | 'ERROR' | 'CONSERVATIVE'
export type Regime = 'TREND' | 'SIDEWAYS' | 'VOLATILE' | 'UNKNOWN'
export type LogLevel = 'DEBUG' | 'INFO' | 'WARN' | 'ERROR'
export type EventType = 'SCAN' | 'FILTER' | 'SCORE' | 'EXEC' | 'TRAIL' | 'BLOCK' | 'SYSTEM'
export type ResultClass = 'pass' | 'reject' | 'block' | 'exec' | 'score' | 'info' | 'adj'

// ─── Market ──────────────────────────────────────────────────────────────────

export interface MarketRegime {
  regime: Regime
  score: number        // 0–100
  vix: number
  adx: number
  trend: number        // 0–100
  momentum: number
  volume: number
  risk: number
}

export interface SystemHealth {
  dataFeed:    { status: 'ok' | 'warn' | 'error'; latency: number }
  orderRouter: { status: 'ok' | 'warn' | 'error'; latency: number }
  riskEngine:  { status: 'ok' | 'warn' | 'error'; latency: number }
  signalGen:   { status: 'ok' | 'warn' | 'error'; latency: number }
}

// ─── Analysis sub-types ───────────────────────────────────────────────────────

export interface NewsItem {
  text: string
  sentiment: 'positive' | 'negative' | 'neutral'
  impact: number   // -1.0 to +1.0
  source: string
  time: string
}

export interface SupplyFlow {
  foreign:     number  // 억원, signed (+매수 / -매도)
  institution: number
  program:     number
  retailNet:   number
  days: number         // consecutive buying days
}

export interface SimilarPattern {
  date: string
  holdDays: number
  returnPct: number
  regime: string
}

export interface FilterStat {
  stage: 1 | 2
  total: number
  passed: number
}

// ─── Candidates ───────────────────────────────────────────────────────────────

export interface Condition {
  key: string
  label: string
  pass: boolean
  value: string
}

export interface Candidate {
  symbol: string
  name: string
  price: number
  changePct: number
  sparkline: number[]
  entryScore: number
  riskScore: number
  confidence: number
  chochGrade: 'A' | 'B' | 'C' | '-'
  volRatio: number
  rsi: number
  conditions: Condition[]
  nearMiss: boolean
  strategy: string
  // Analysis scores (0–10)
  newsScore: number
  supplyScore: number
  technicalScore: number
  filterStage: 1 | 2        // which stage this passed
  aiExpectation: number     // expected return %
}

// ─── Chart ───────────────────────────────────────────────────────────────────

export interface OHLCV {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface ScoreDimension {
  name: string
  score: number
  weight: number
  details: string
}

export interface CandidateDetail {
  symbol: string
  ohlcv: OHLCV[]
  scores: ScoreDimension[]
  totalScore: number
  entryReason: string
  sl: number
  tp: number
  rrRatio: number
  positionSize: number
  entryIndex?: number
  // Research card data
  newsSummary: string
  newsItems: NewsItem[]
  supplySummary: string
  supplyFlow: SupplyFlow
  technicalSummary: string
  aiExpectation: number
  similarPatterns: SimilarPattern[]
  filterPassReason: string
}

// ─── Decision Log ─────────────────────────────────────────────────────────────

export interface DecisionEvent {
  id: string
  time: string           // HH:MM:SS.mmm
  type: EventType
  symbol: string
  symbolName?: string
  event: string
  params: string
  result: string
  resultClass: ResultClass
  fnRef?: string
  expanded?: boolean
  detail?: string
}

export interface DebugLog {
  id: string
  level: LogLevel
  time: string
  module: string
  msg: string
}

// ─── Positions & Trades ───────────────────────────────────────────────────────

export interface Position {
  symbol: string
  name: string
  entryPrice: number
  currentPrice: number
  quantity: number
  sl: number
  tp: number
  pnl: number
  pnlPct: number
  strategy: string
  holdMinutes: number
  chochGrade: string
}

export interface Trade {
  id: string
  symbol: string
  name: string
  strategy: string
  entryPrice: number
  exitPrice: number
  quantity: number
  pnl: number
  pnlPct: number
  win: boolean
  duration: string
  exitReason: string
  exitTag: 'TP_HIT' | 'SL_HIT' | 'TRAIL_STOP' | 'EF' | 'TIME' | 'VWAP' | 'HARD_STOP' | 'OTHER'
  time: string
  // For GOOD/BAD analysis
  newsScoreAtEntry?: number
  supplyScoreAtEntry?: number
  technicalScoreAtEntry?: number
}

// ─── Performance ─────────────────────────────────────────────────────────────

export interface PeriodPerf {
  pnl: number
  pct: number
  trades?: number
  winRate?: number
}

export interface StrategyPerf {
  code: string
  name: string
  winRate: number
  avgReturn: number
  trades: number
  sharpe: number
  maxDD: number
}

export interface RiskMetric {
  label: string
  value: string
  status: 'ok' | 'warn' | 'critical'
  description: string
}

// ─── Parameters ──────────────────────────────────────────────────────────────

export interface Param {
  key: string
  label: string
  value: number | string | boolean
  defaultValue: number | string | boolean
  type: 'number' | 'select' | 'boolean'
  min?: number
  max?: number
  step?: number
  options?: string[]
  description: string
  dirty?: boolean
}
