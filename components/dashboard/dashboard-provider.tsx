'use client'

import { useEffect } from 'react'
import { useDashboardInit } from '@/hooks/useDashboardInit'

/**
 * Thin client wrapper that boots the dashboard data layer.
 * Must be rendered inside the layout so hooks have access to the React tree.
 */
export function DashboardProvider({ children }: { children: React.ReactNode }) {
  useDashboardInit()
  return <>{children}</>
}
