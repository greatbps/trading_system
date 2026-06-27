'use client'

import { create } from 'zustand'
import type {
  Candidate,
  CandidateDetail,
  DecisionEvent,
  DebugLog,
  Position,
  Trade,
  MarketRegime,
  SystemHealth,
  StrategyPerf,
  RiskMetric,
  Param,
  PeriodPerf,
  FilterStat,
} from '@/src/types/trading'

// ─── Types ────────────────────────────────────────────────────────────────────

type PanelId = 'params' | 'risk' | 'errors' | 'report' | null

interface StrategyToggles {
  MOM: boolean
  TRD: boolean
  MRV: boolean
  SMC: boolean
}

interface TradingState {
  // Market
  marketRegime: MarketRegime | null
  systemHealth: SystemHealth | null

  // Candidates
  candidates: Candidate[]
  selectedSymbol: string | null
  selectedDetail: CandidateDetail | null

  // Decision log
  decisionLog: DecisionEvent[]
  debugLogs: DebugLog[]
  logFilter: string   // event type filter: 'ALL' | 'EXEC' | 'FILTER' | ...
  logSearch: string

  // Positions & trades
  positions: Position[]
  trades: Trade[]
  tradesPeriod: { days: number; from: string; to: string; label: string } | null
  tradesDateRange: { from: string; to: string }

  // Performance
  periodPerf: { today: PeriodPerf; week: PeriodPerf; month: PeriodPerf } | null
  strategyPerf: StrategyPerf[]
  riskMetrics: RiskMetric[]

  // Parameters
  params: Param[]

  // Filter stats
  filterStats: FilterStat[]

  // UI state
  activePanel: PanelId
  strategyToggles: StrategyToggles
  goodBadView: boolean   // toggle GOOD/BAD trade comparison

  // Account
  account: {
    deposit: number
    holdingValue: number
    totalAssets: number
    dailyPnl: number
    weeklyPnl: number
    consecutiveLosses: number
  } | null

  // Mode
  isLive: boolean
}

interface TradingActions {
  // Market
  setMarket: (regime: MarketRegime, health: SystemHealth) => void

  // Candidates
  setCandidates: (candidates: Candidate[]) => void
  selectSymbol: (symbol: string) => void
  setSelectedDetail: (detail: CandidateDetail) => void

  // Decision log
  setDecisionLog: (events: DecisionEvent[]) => void
  appendDecisionEvent: (event: DecisionEvent) => void
  appendDebugLog: (log: DebugLog) => void
  setLogFilter: (filter: string) => void
  setLogSearch: (search: string) => void

  // Positions & trades
  setPositions: (positions: Position[]) => void
  setTrades: (trades: Trade[], period?: { days: number; from: string; to: string; label: string } | null) => void
  setTradesDateRange: (range: { from: string; to: string }) => void

  // Performance
  setPerformance: (data: {
    today: PeriodPerf
    week: PeriodPerf
    month: PeriodPerf
    strategies: StrategyPerf[]
    riskMetrics: RiskMetric[]
  }) => void

  // Parameters
  setParams: (params: Param[]) => void
  updateParam: (key: string, value: Param['value']) => void

  // Filter stats
  setFilterStats: (stats: FilterStat[]) => void

  // Account
  setAccount: (account: NonNullable<TradingState['account']>) => void

  // UI
  togglePanel: (panel: Exclude<PanelId, null>) => void
  closePanel: () => void
  toggleStrategy: (strategy: keyof StrategyToggles) => void
  toggleGoodBad: () => void
  setLive: (live: boolean) => void
}

// ─── Store ────────────────────────────────────────────────────────────────────

export const useTradingStore = create<TradingState & TradingActions>((set) => ({
  // Initial state
  marketRegime: null,
  systemHealth: null,
  candidates: [],
  selectedSymbol: null,
  selectedDetail: null,
  decisionLog: [],
  debugLogs: [],
  logFilter: 'ALL',
  logSearch: '',
  positions: [],
  trades: [],
  tradesPeriod: null,
  tradesDateRange: (() => {
    const to   = new Date()
    const from = new Date(to); from.setDate(from.getDate() - 6)
    return { from: from.toISOString().slice(0, 10), to: to.toISOString().slice(0, 10) }
  })(),
  periodPerf: null,
  strategyPerf: [],
  riskMetrics: [],
  params: [],
  filterStats: [],
  account: null,
  activePanel: null,
  strategyToggles: { MOM: true, TRD: true, MRV: false, SMC: true },
  goodBadView: false,
  isLive: false,

  // Market
  setMarket: (regime, health) => set({ marketRegime: regime, systemHealth: health }),

  // Candidates
  setCandidates: (candidates) => set({ candidates }),
  selectSymbol: (symbol) => set({ selectedSymbol: symbol }),
  setSelectedDetail: (detail) => set({ selectedDetail: detail }),

  // Decision log — keep max 500 events in memory
  setDecisionLog: (events) => set({ decisionLog: events }),
  appendDecisionEvent: (event) =>
    set((state) => ({
      decisionLog: [event, ...state.decisionLog].slice(0, 500),
    })),
  appendDebugLog: (log) =>
    set((state) => ({
      debugLogs: [log, ...state.debugLogs].slice(0, 200),
    })),
  setLogFilter: (logFilter) => set({ logFilter }),
  setLogSearch: (logSearch) => set({ logSearch }),

  // Positions & trades
  setPositions: (positions) => set({ positions }),
  setTrades: (trades, period) => set({ trades, ...(period !== undefined ? { tradesPeriod: period ?? null } : {}) }),
  setTradesDateRange: (tradesDateRange) => set({ tradesDateRange }),

  // Performance
  setPerformance: ({ today, week, month, strategies, riskMetrics }) =>
    set({
      periodPerf: { today, week, month },
      strategyPerf: strategies,
      riskMetrics,
    }),

  // Parameters
  setParams: (params) => set({ params }),
  updateParam: (key, value) =>
    set((state) => ({
      params: state.params.map((p) =>
        p.key === key ? { ...p, value, dirty: p.value !== value } : p
      ),
    })),

  // Filter stats
  setFilterStats: (filterStats) => set({ filterStats }),

  // Account
  setAccount: (account) => set({ account }),

  // UI
  togglePanel: (panel) =>
    set((state) => ({ activePanel: state.activePanel === panel ? null : panel })),
  closePanel: () => set({ activePanel: null }),
  toggleStrategy: (strategy) =>
    set((state) => ({
      strategyToggles: {
        ...state.strategyToggles,
        [strategy]: !state.strategyToggles[strategy],
      },
    })),
  toggleGoodBad: () => set((state) => ({ goodBadView: !state.goodBadView })),
  setLive: (isLive) => set({ isLive }),
}))

// ─── Selectors ────────────────────────────────────────────────────────────────

export const selectFilteredLog = (state: TradingState) => {
  const { decisionLog, logFilter, logSearch } = state
  return decisionLog.filter((e) => {
    const typeOk = logFilter === 'ALL' || e.type === logFilter
    const searchOk =
      !logSearch ||
      e.symbol.toLowerCase().includes(logSearch.toLowerCase()) ||
      e.event.toLowerCase().includes(logSearch.toLowerCase()) ||
      e.params.toLowerCase().includes(logSearch.toLowerCase())
    return typeOk && searchOk
  })
}
