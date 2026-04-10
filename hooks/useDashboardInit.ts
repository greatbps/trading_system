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
export function useDashboardInit(): void {
  const {
    setMarket, setCandidates, setDecisionLog,
    setPositions, setTrades, setPerformance,
    setParams, setFilterStats, selectedSymbol, setSelectedDetail,
  } = useTradingStore()

  // ── One-time init ────────────────────────────────────────────────────────
  useEffect(() => {
    const init = async () => {
      const [market, candidates, log, positions, trades, perf, params, filterStats] =
        await Promise.allSettled([
          fetchMarket(),
          fetchCandidates(),
          fetchDecisionLog(),
          fetchPositions(),
          fetchTrades(),
          fetchPerformance(),
          fetchParams(),
          fetchFilterStats(),
        ])

      if (market.status === 'fulfilled')      setMarket(market.value.regime, market.value.health)
      if (candidates.status === 'fulfilled')  setCandidates(candidates.value)
      if (log.status === 'fulfilled')         setDecisionLog(log.value)
      if (positions.status === 'fulfilled')   setPositions(positions.value)
      if (trades.status === 'fulfilled')      setTrades(trades.value)
      if (perf.status === 'fulfilled')        setPerformance(perf.value)
      if (params.status === 'fulfilled')      setParams(params.value)
      if (filterStats.status === 'fulfilled') setFilterStats(filterStats.value)
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
    const p = await fetchPositions()
    setPositions(p)
    const t = await fetchTrades()
    setTrades(t)
  }, 15000)

  // ── Fetch detail when symbol changes ────────────────────────────────────
  useEffect(() => {
    if (!selectedSymbol) return
    fetchCandidateDetail(selectedSymbol).then(setSelectedDetail).catch(() => {})
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSymbol])

  // ── Mock realtime logs ───────────────────────────────────────────────────
  useRealtimeLogs()
}
