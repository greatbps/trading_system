'use client'

import { Component, type ReactNode } from 'react'
import { useTradingStore } from '@/store/trading'
import { ReportPanel } from '@/components/dashboard/report-panel'
import { ParamsPanel } from '@/components/dashboard/params-panel'
import { ErrorsPanel } from '@/components/dashboard/errors-panel'

// ─── Error boundary so a panel crash doesn't kill the whole page ──────────────

interface EBState { err: string | null }

class PanelErrorBoundary extends Component<{ children: ReactNode; onClose: () => void }, EBState> {
  constructor(props: { children: ReactNode; onClose: () => void }) {
    super(props)
    this.state = { err: null }
  }
  static getDerivedStateFromError(e: Error) { return { err: e.message } }

  render() {
    if (this.state.err) {
      return (
        <div className="flex flex-col h-full w-80 border-l border-border bg-card overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-muted/20 shrink-0">
            <span className="text-[12px] font-bold text-destructive">패널 오류</span>
            <button className="text-[11px] text-muted-foreground" onClick={this.props.onClose}>닫기</button>
          </div>
          <div className="flex-1 flex items-center justify-center p-4">
            <span className="text-[11px] text-destructive font-mono break-all">{this.state.err}</span>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

// ─── Overlay ──────────────────────────────────────────────────────────────────

export function PanelOverlay() {
  const { activePanel, closePanel } = useTradingStore()

  if (!activePanel) return null

  return (
    <div
      className="fixed inset-0 z-50 flex"
      onClick={(e) => { if (e.target === e.currentTarget) closePanel() }}
    >
      <div className="flex-1" onClick={closePanel} />
      <PanelErrorBoundary onClose={closePanel}>
        {activePanel === 'params' && <ParamsPanel />}
        {activePanel === 'errors' && <ErrorsPanel />}
        {activePanel === 'report' && <ReportPanel />}
      </PanelErrorBoundary>
    </div>
  )
}
