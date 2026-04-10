"use client"

import { useEffect, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Terminal, Clock, Wifi, Database, Zap, Settings, Bell } from "lucide-react"
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

export function TopBar() {
  const { strategyToggles, toggleStrategy, systemHealth, positions, trades, periodPerf, togglePanel } =
    useTradingStore()

  const todayPnl   = periodPerf?.today.pnl ?? 0
  const todayPct   = periodPerf?.today.pct ?? 0
  const posCount   = positions.length
  const tradeCount = trades.length

  const dataLatency = systemHealth?.dataFeed.latency    ?? 0
  const apiLatency  = systemHealth?.signalGen.latency   ?? 0
  const wsStatus    = systemHealth?.orderRouter.status  ?? 'ok'

  const pnlColor = todayPnl >= 0 ? "text-success" : "text-destructive"
  const pnlSign  = todayPnl >= 0 ? "+" : ""

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

        <div className="flex items-center gap-3">
          {(["MOM", "TRD", "MRV", "SMC"] as const).map((s) => (
            <div key={s} className="flex items-center gap-1.5">
              <span className={cn(
                "font-mono text-[12px]",
                strategyToggles[s] ? "text-foreground" : "text-muted-foreground"
              )}>{s}</span>
              <Switch
                checked={strategyToggles[s]}
                onCheckedChange={() => toggleStrategy(s)}
                className="h-3 w-6 data-[state=checked]:bg-success [&>span]:h-2 [&>span]:w-2"
              />
            </div>
          ))}
        </div>
      </div>

      {/* Center: System Metrics */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <Database className="h-3 w-3 text-muted-foreground" />
          <span className="font-mono text-[12px] text-muted-foreground">DATA</span>
          <span className={cn(
            "font-mono text-[12px]",
            dataLatency < 10 ? "text-success" : dataLatency < 50 ? "text-warning" : "text-destructive"
          )}>{dataLatency}ms</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Wifi className={cn("h-3 w-3", wsStatus === "ok" ? "text-success" : "text-warning")} />
          <span className="font-mono text-[12px] text-muted-foreground">WS</span>
          <span className={cn(
            "font-mono text-[12px]",
            wsStatus === "ok" ? "text-success" : "text-warning"
          )}>{wsStatus.toUpperCase()}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Zap className="h-3 w-3 text-muted-foreground" />
          <span className="font-mono text-[12px] text-muted-foreground">SIG</span>
          <span className={cn(
            "font-mono text-[12px]",
            apiLatency < 20 ? "text-success" : apiLatency < 60 ? "text-warning" : "text-destructive"
          )}>{apiLatency}ms</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Clock className="h-3 w-3 text-muted-foreground" />
          <LiveClock />
        </div>
      </div>

      {/* Right: P&L + Status + Actions */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-[12px] text-muted-foreground">POS</span>
            <span className="font-mono text-[12px] text-foreground">{posCount}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-[12px] text-muted-foreground">TRADES</span>
            <span className="font-mono text-[12px] text-foreground">{tradeCount}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-[12px] text-muted-foreground">P&L</span>
            <span className={cn("font-mono text-[12px] font-semibold", pnlColor)}>
              {pnlSign}{(todayPnl / 10000).toFixed(0)}만
            </span>
            <span className={cn("font-mono text-[11px]", pnlColor)}>
              ({pnlSign}{todayPct.toFixed(2)}%)
            </span>
          </div>
        </div>

        <div className="h-4 w-px bg-border" />

        <div className="flex items-center gap-1.5">
          <Badge className="bg-success/20 px-1.5 py-0 font-mono text-[11px] text-success">
            <span className="mr-1 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-success" />
            DEMO
          </Badge>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={() => togglePanel('params')}
          >
            <Settings className="h-3 w-3" />
          </Button>
          <Button variant="ghost" size="icon" className="h-6 w-6">
            <Bell className="h-3 w-3" />
          </Button>
        </div>
      </div>
    </header>
  )
}
