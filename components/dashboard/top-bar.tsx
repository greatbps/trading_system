"use client"

import { useEffect, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Terminal, Clock, Wifi, Database, Zap, Settings, Bell, BarChart2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { useTradingStore } from "@/store/trading"


function LiveClock() {
  const [time, setTime] = useState("")
  useEffect(() => {
    const update = () => setTime(new Date().toLocaleTimeString("ko-KR", { hour12: false }))
    update()
    const id = setInterval(update, 1000)
    return () => clearInterval(id)
  }, [])
  return <span className="font-mono text-[12px] text-foreground">{time} KST</span>
}

function latencyColor(ms: number, warn: number, danger: number): string {
  if (ms < warn)   return "text-success"
  if (ms < danger) return "text-yellow-400"
  return "text-destructive"
}

function latencyBg(ms: number, warn: number, danger: number): string {
  if (ms >= danger) return "bg-destructive/20"
  if (ms >= warn)   return "bg-yellow-400/10"
  return ""
}

export function TopBar() {
  const { strategyToggles, toggleStrategy, systemHealth, positions, trades, periodPerf, togglePanel, params } =
    useTradingStore()

  const todayPnl   = periodPerf?.today.pnl ?? 0
  const todayPct   = periodPerf?.today.pct ?? 0
  const posCount   = positions.length
  const tradeCount = trades.length

  const dataLatency  = systemHealth?.dataFeed.latency    ?? 0
  const apiLatency   = systemHealth?.signalGen.latency   ?? 0
  const orderLatency = systemHealth?.orderRouter.latency ?? 0
  const riskLatency  = systemHealth?.riskEngine.latency  ?? 0
  const wsStatus     = systemHealth?.orderRouter.status  ?? 'ok'

  const pnlColor = todayPnl >= 0 ? "text-success" : "text-destructive"
  const pnlSign  = todayPnl >= 0 ? "+" : ""

  const dryRun = params.find(p => p.key === 'dry_run')?.value
  const isLive = dryRun === false || dryRun === 'false'

  return (
    <header className="flex h-10 shrink-0 items-center justify-between border-b border-border bg-card px-3">
      {/* Left: Logo + Strategy Toggles */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <Terminal className="h-4 w-4 text-success" />
          <span className="font-mono text-sm font-bold tracking-tight">
            TRADE<span className="text-success">OS</span>
          </span>
          <Badge className="ml-1 bg-accent px-1 py-0 font-mono text-[10px] text-muted-foreground">
            v2.4.1
          </Badge>
        </div>

        <div className="h-4 w-px bg-border" />

        {/* 페이지 네비게이션 */}
        <a
          href="/trading/"
          className="px-2.5 py-1 rounded text-[11px] font-mono border border-success/50 text-success bg-success/10 hover:bg-success/20 transition-colors"
        >
          대시보드
        </a>
        <a
          href="/trading/optimize/"
          className="px-2.5 py-1 rounded text-[11px] font-mono border border-success/50 text-success bg-success/10 hover:bg-success/20 transition-colors"
        >
          전략 최적화
        </a>

        <div className="h-4 w-px bg-border" />

        {/* 전략 ON/OFF — Switch 제거, 도트 표시 */}
        <div className="flex items-center gap-2">
          {(["MOM", "TRD", "MRV", "SMC"] as const).map((s) => {
            const on = strategyToggles[s]
            return (
              <a
                key={s}
                role="button"
                onClick={() => toggleStrategy(s)}
                className={cn(
                  "cursor-pointer px-2.5 py-1 rounded text-[11px] font-mono border transition-colors",
                  on
                    ? "border-success/50 text-success bg-success/10 hover:bg-success/20"
                    : "border-border text-muted-foreground hover:text-foreground hover:border-foreground/50"
                )}
              >
                {s}
              </a>
            )
          })}
        </div>
      </div>

      {/* Center: System Metrics */}
      <div className="flex items-center gap-3">
        {/* DATA latency */}
        <div className={cn(
          "flex items-center gap-1 px-1.5 py-0.5 rounded",
          latencyBg(dataLatency, 300, 1000)
        )}>
          <Database className={cn("h-3 w-3", latencyColor(dataLatency, 300, 1000))} />
          <span className="font-mono text-[12px] text-muted-foreground">DATA</span>
          <span className={cn("font-mono text-[12px]", latencyColor(dataLatency, 300, 1000))}>
            {dataLatency}ms
          </span>
          {dataLatency >= 1000 && <span className="text-[9px] text-destructive font-bold">!</span>}
        </div>

        {/* WS status */}
        <div className="flex items-center gap-1">
          <Wifi className={cn(
            "h-3 w-3",
            wsStatus === "ok"            ? "text-success"     :
            wsStatus === "reconnecting"  ? "text-yellow-400"  : "text-destructive"
          )} />
          <span className="font-mono text-[12px] text-muted-foreground">WS</span>
          <span className={cn(
            "font-mono text-[12px]",
            wsStatus === "ok"            ? "text-success"    :
            wsStatus === "reconnecting"  ? "text-yellow-400" : "text-destructive"
          )}>{wsStatus.toUpperCase()}</span>
        </div>

        {/* ORDR latency */}
        <div className={cn(
          "flex items-center gap-1 px-1.5 py-0.5 rounded",
          latencyBg(orderLatency, 200, 500)
        )}>
          <span className="font-mono text-[12px] text-muted-foreground">ORDR</span>
          <span className={cn("font-mono text-[12px]", latencyColor(orderLatency, 200, 500))}>
            {orderLatency}ms
          </span>
        </div>

        {/* RISK status */}
        <div className={cn(
          "flex items-center gap-1 px-1.5 py-0.5 rounded",
          latencyBg(riskLatency, 200, 500)
        )}>
          <span className="font-mono text-[12px] text-muted-foreground">RISK</span>
          <span className={cn("font-mono text-[12px]", latencyColor(riskLatency, 200, 500))}>
            {riskLatency}ms
          </span>
        </div>

        {/* SIG latency */}
        <div className={cn(
          "flex items-center gap-1 px-1.5 py-0.5 rounded",
          latencyBg(apiLatency, 200, 500)
        )}>
          <Zap className={cn("h-3 w-3", latencyColor(apiLatency, 200, 500))} />
          <span className="font-mono text-[12px] text-muted-foreground">SIG</span>
          <span className={cn("font-mono text-[12px]", latencyColor(apiLatency, 200, 500))}>
            {apiLatency}ms
          </span>
          {apiLatency >= 500 && <span className="text-[9px] text-destructive font-bold">!</span>}
        </div>

        {/* SYSTEM HEALTH aggregate */}
        {(() => {
          const allOk = wsStatus === 'ok' && dataLatency < 300 && orderLatency < 200 && apiLatency < 200 && riskLatency < 200
          const anyError = wsStatus === 'error' || dataLatency >= 1000 || orderLatency >= 500 || apiLatency >= 500
          const health = anyError ? 'CRITICAL' : allOk ? 'GOOD' : 'DEGRADED'
          const hColor = health === 'GOOD' ? 'text-success' : health === 'DEGRADED' ? 'text-yellow-400' : 'text-destructive'
          const hDot   = health === 'GOOD' ? 'bg-success' : health === 'DEGRADED' ? 'bg-yellow-400' : 'bg-destructive'

          // Human-readable reason
          let reason = ''
          if (health !== 'GOOD') {
            if (wsStatus === 'error') reason = 'Connection lost'
            else if (dataLatency >= 1000) reason = 'Data feed timeout'
            else if (orderLatency >= 500) reason = 'Execution delay'
            else if (apiLatency >= 500) reason = 'Signal delay'
            else if (riskLatency >= 500) reason = 'Risk engine slow'
            else if (dataLatency >= 300) reason = 'Data feed slow'
            else if (orderLatency >= 200) reason = 'Order latency high'
            else reason = 'Performance degraded'
          }

          return (
            <div className="flex items-center gap-1 rounded border border-border/50 px-1.5 py-0.5">
              <span className={cn("inline-block h-1.5 w-1.5 rounded-full", health === 'GOOD' ? 'animate-pulse ' + hDot : hDot)} />
              <span className="font-mono text-[11px] text-muted-foreground">SYS</span>
              <span className={cn("font-mono text-[11px] font-semibold", hColor)}>{health}</span>
              {reason && <span className="font-mono text-[10px] text-muted-foreground/70">({reason})</span>}
            </div>
          )
        })()}

        <div className="flex items-center gap-1">
          <Clock className="h-3 w-3 text-muted-foreground" />
          <LiveClock />
        </div>
      </div>

      {/* Right: P&L + Status + Actions */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            <span className="font-mono text-[12px] text-muted-foreground">POS</span>
            <span className={cn(
              "font-mono text-[12px] font-semibold",
              posCount > 0 ? "text-foreground" : "text-muted-foreground"
            )}>{posCount}</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="font-mono text-[12px] text-muted-foreground">TRD</span>
            <span className="font-mono text-[12px] text-foreground">{tradeCount}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-[12px] text-muted-foreground">P&L</span>
            <span className={cn("font-mono text-[12px] font-bold", pnlColor)}>
              {pnlSign}₩{Math.abs(todayPnl).toLocaleString()}
            </span>
            <span className={cn("font-mono text-[11px]", pnlColor)}>
              ({pnlSign}{todayPct.toFixed(2)}%)
            </span>
          </div>
        </div>

        <div className="h-4 w-px bg-border" />

        <div className="flex items-center gap-1.5">
          {/* LIVE / DEMO 배지 */}
          {isLive ? (
            <Badge className="bg-destructive/20 px-1.5 py-0 font-mono text-[11px] text-destructive border border-destructive/40">
              <span className="mr-1 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-destructive" />
              LIVE
            </Badge>
          ) : (
            <Badge className="bg-muted/40 px-1.5 py-0 font-mono text-[11px] text-muted-foreground border border-border">
              <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full bg-muted-foreground/50" />
              DEMO
            </Badge>
          )}

          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={() => togglePanel('report')}
            title="일일 리포트"
          >
            <BarChart2 className="h-3 w-3" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={() => togglePanel('params')}
            title="파라미터 설정"
          >
            <Settings className="h-3 w-3" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={() => togglePanel('errors')}
            title="알림·로그"
          >
            <Bell className="h-3 w-3" />
          </Button>

        </div>
      </div>
    </header>
  )
}
