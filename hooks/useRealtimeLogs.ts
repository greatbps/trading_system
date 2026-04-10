'use client'

import { useEffect, useRef } from 'react'
import { useTradingStore } from '@/store/trading'
import { generateDecisionEvent, generateDebugLog } from '@/src/lib/mock'

/**
 * In mock/demo mode: feeds synthetic decision events and debug logs into the
 * store on a randomised cadence so the UI feels alive without a real backend.
 *
 * In live mode (store.isLive === true) this hook does nothing — the backend
 * pushes data via the polling hooks instead.
 */
export function useRealtimeLogs(): void {
  const isLive = useTradingStore((s) => s.isLive)
  const appendDecisionEvent = useTradingStore((s) => s.appendDecisionEvent)
  const appendDebugLog = useTradingStore((s) => s.appendDebugLog)

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const debugTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (isLive) return

    // Decision events: random cadence 1.5s–5s
    const scheduleNext = () => {
      const delay = 1500 + Math.random() * 3500
      timerRef.current = setTimeout(() => {
        appendDecisionEvent(generateDecisionEvent())
        scheduleNext()
      }, delay)
    }

    scheduleNext()

    // Debug logs: every 2s
    debugTimerRef.current = setInterval(() => {
      appendDebugLog(generateDebugLog())
    }, 2000)

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
      if (debugTimerRef.current) clearInterval(debugTimerRef.current)
    }
  }, [isLive, appendDecisionEvent, appendDebugLog])
}
