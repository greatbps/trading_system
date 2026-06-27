'use client'

import { useEffect } from 'react'
import { useTradingStore } from '@/store/trading'
import {
  fetchMarket,
  fetchCandidates,
  fetchCandidateDetail,
  fetchDecisionLog,
  fetchPositions,
  fetchTrades,
  fetchPerformance,
  fetchParams,
  fetchFilterStats,
  fetchAccount,
} from '@/lib/api'
import { usePolling } from '@/hooks/usePolling'
import { useRealtimeLogs } from '@/hooks/useRealtimeLogs'

/**
 * One-stop hook that bootstraps the entire dashboard:
 * - Initial data load on mount
 * - Polling intervals for live data
 * - Realtime log simulation in mock mode
 *
 * Mount this once at the page/layout level.
 */
const USE_REAL = process.env.NEXT_PUBLIC_USE_REAL_API === 'true'

export function useDashboardInit(): void {
  const {
    setMarket, setCandidates, setDecisionLog,
    setPositions, setTrades, setPerformance,
    setParams, setFilterStats, setAccount,
    selectedSymbol, selectSymbol, setSelectedDetail,
    candidates, setLive,
    tradesDateRange,
  } = useTradingStore()

  // ── Switch to live mode immediately if real API is configured ───────────
  useEffect(() => {
    if (USE_REAL) setLive(true)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── One-time init ────────────────────────────────────────────────────────
  useEffect(() => {
    const init = async () => {
      const [market, candidates, log, positions, trades, perf, params, filterStats, account] =
        await Promise.allSettled([
          fetchMarket(),
          fetchCandidates(),
          fetchDecisionLog(),
          fetchPositions(),
          fetchTrades(),
          fetchPerformance(),
          fetchParams(),
          fetchFilterStats(),
          fetchAccount(),
        ])

      if (market.status === 'fulfilled')      setMarket(market.value.regime, market.value.health)
      if (candidates.status === 'fulfilled')  setCandidates(candidates.value)
      if (log.status === 'fulfilled')         setDecisionLog(log.value)
      if (positions.status === 'fulfilled')   setPositions(positions.value)
      if (trades.status === 'fulfilled')      setTrades(trades.value.trades, trades.value.period)
      if (perf.status === 'fulfilled')        setPerformance(perf.value)
      if (params.status === 'fulfilled')      setParams(params.value)
      if (filterStats.status === 'fulfilled') setFilterStats(filterStats.value)
      if (account.status === 'fulfilled')     setAccount(account.value)
    }
    init()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── Polling intervals ────────────────────────────────────────────────────
  usePolling(async () => {
    const m = await fetchMarket()
    setMarket(m.regime, m.health)
  }, 5000)

  usePolling(async () => {
    const c = await fetchCandidates()
    setCandidates(c)
  }, 10000)

  usePolling(async () => {
    const [p, t, a] = await Promise.all([
      fetchPositions(),
      fetchTrades({ from: tradesDateRange.from, to: tradesDateRange.to }),
      fetchAccount(),
    ])
    setPositions(p)
    setTrades(t.trades, t.period)
    setAccount(a)
  }, 15000)

  // ── tradesDateRange 변경 시 즉시 재조회 ─────────────────────────────────
  useEffect(() => {
    fetchTrades({ from: tradesDateRange.from, to: tradesDateRange.to })
      .then((t) => setTrades(t.trades, t.period))
      .catch(console.error)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tradesDateRange.from, tradesDateRange.to])

  // ── Decision log polling (live signal feed) ──────────────────────────────
  usePolling(async () => {
    const log = await fetchDecisionLog()
    setDecisionLog(log)
  }, 5000)

  // ── 후보 로드되면 첫 종목 자동 선택 ─────────────────────────────────────
  useEffect(() => {
    if (candidates.length > 0 && !selectedSymbol) {
      selectSymbol(candidates[0].symbol)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candidates])

  // ── Fetch detail when symbol changes ────────────────────────────────────
  useEffect(() => {
    if (!selectedSymbol) return
    fetchCandidateDetail(selectedSymbol).then(setSelectedDetail).catch(console.error)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSymbol])

  // ── Mock realtime logs ───────────────────────────────────────────────────
  useRealtimeLogs()
}
