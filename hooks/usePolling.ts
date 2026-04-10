'use client'

import { useEffect, useRef } from 'react'

/**
 * Runs `fn` immediately and then every `intervalMs`.
 * Stops if the component unmounts or `enabled` becomes false.
 */
export function usePolling(
  fn: () => Promise<void> | void,
  intervalMs: number,
  enabled = true
): void {
  const fnRef = useRef(fn)
  fnRef.current = fn

  useEffect(() => {
    if (!enabled) return

    let cancelled = false

    const run = async () => {
      if (cancelled) return
      try {
        await fnRef.current()
      } catch {
        // silently skip failed polls — component decides what to surface
      }
    }

    run()
    const id = setInterval(run, intervalMs)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [intervalMs, enabled])
}
