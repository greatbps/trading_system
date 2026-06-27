"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { cn } from "@/lib/utils"
import { useState } from "react"
import {
  Receipt, GitCompare, Layers, AlertTriangle,
  ArrowUpRight, ArrowDownRight,
  ThumbsUp, ThumbsDown,
  TrendingUp, TrendingDown, Minus, Wallet,
  CalendarRange,
} from "lucide-react"
import { useTradingStore } from "@/store/trading"
import type { Trade } from "@/src/types/trading"

// ─── Date Range Picker ────────────────────────────────────────────────────────

const PRESETS = [
  { label: '7일',  days: 7  },
  { label: '14일', days: 14 },
  { label: '30일', days: 30 },
]

function todayStr() {
  return new Date().toISOString().slice(0, 10)
}

function daysAgoStr(n: number) {
  const d = new Date(); d.setDate(d.getDate() - (n - 1))
  return d.toISOString().slice(0, 10)
}

function DateRangePicker() {
  const { tradesDateRange, setTradesDateRange } = useTradingStore()
  const [activePreset, setActivePreset] = useState<number | null>(7)

  const applyPreset = (days: number) => {
    setActivePreset(days)
    setTradesDateRange({ from: daysAgoStr(days), to: todayStr() })
  }

  const handleFrom = (e: React.ChangeEvent<HTMLInputElement>) => {
    setActivePreset(null)
    setTradesDateRange({ from: e.target.value, to: tradesDateRange.to })
  }

  const handleTo = (e: React.ChangeEvent<HTMLInputElement>) => {
    setActivePreset(null)
    setTradesDateRange({ from: tradesDateRange.from, to: e.target.value })
  }

  return (
    <div className="flex flex-col gap-1.5 rounded-md border border-border bg-card px-2 py-1.5">
      <div className="flex items-center gap-1.5 font-mono text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
        <CalendarRange className="h-3 w-3" />
        <span>기간 선택</span>
        <div className="ml-auto flex items-center gap-1">
          {PRESETS.map(({ label, days }) => (
            <button
              key={days}
              onClick={() => applyPreset(days)}
              className={cn(
                "rounded px-1.5 py-0.5 font-mono text-[10px] transition-colors",
                activePreset === days
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
              )}
            >{label}</button>
          ))}
        </div>
      </div>
      <div className="flex items-center gap-1">
        <input
          type="date"
          value={tradesDateRange.from}
          max={tradesDateRange.to}
          onChange={handleFrom}
          className="flex-1 rounded border border-border bg-background px-1 py-0.5 font-mono text-[11px] text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
        />
        <span className="font-mono text-[10px] text-muted-foreground">~</span>
        <input
          type="date"
          value={tradesDateRange.to}
          min={tradesDateRange.from}
          max={todayStr()}
          onChange={handleTo}
          className="flex-1 rounded border border-border bg-background px-1 py-0.5 font-mono text-[11px] text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </div>
    </div>
  )
}

// ─── Trade Bias ───────────────────────────────────────────────────────────────

function TradeBias() {
  const marketRegime = useTradingStore((s) => s.marketRegime)

  if (!marketRegime) return null

  const bias: 'LONG' | 'SKIP' | 'WATCH' =
    marketRegime.regime === 'TREND' && marketRegime.score >= 65 && marketRegime.risk < 60 ? 'LONG' :
    marketRegime.regime === 'VOLATILE' || marketRegime.risk >= 75 ? 'SKIP' :
    'WATCH'

  const isStrong = bias === 'LONG' && marketRegime.score >= 75 && marketRegime.risk < 45
  const riskLevel = marketRegime.risk >= 70 ? 'HIGH' : marketRegime.risk >= 45 ? 'MED' : 'LOW'
  const riskColor = riskLevel === 'HIGH' ? 'text-destructive' : riskLevel === 'MED' ? 'text-warning' : 'text-success'

  const biasConfig = {
    LONG:  { color: 'text-success',     bg: 'bg-success/10 border-success/30',         Icon: TrendingUp  },
    SKIP:  { color: 'text-destructive', bg: 'bg-destructive/10 border-destructive/30', Icon: TrendingDown },
    WATCH: { color: 'text-warning',     bg: 'bg-warning/10 border-warning/30',         Icon: Minus       },
  }
  const { color, bg, Icon } = biasConfig[bias]

  const reasons = [
    marketRegime.regime === 'TREND' ? '추세장' : marketRegime.regime === 'SIDEWAYS' ? '횡보장' : '변동성',
    `모멘텀 ${marketRegime.momentum}`,
  ]

  return (
    <Card className={cn("shrink-0 border py-1", bg)}>
      <CardContent className="px-3 py-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <Icon className={cn("h-4 w-4", color)} />
            <span className="font-mono text-[11px] text-muted-foreground uppercase tracking-wider">TRADE BIAS</span>
          </div>
          <span className={cn("font-mono text-xl font-bold tracking-wide", color)}>
            {isStrong ? '★ ' : ''}{bias}
          </span>
        </div>
        <div className="mt-1 flex items-center justify-between">
          <div className="flex items-center gap-2">
            {reasons.map((r) => (
              <span key={r} className="font-mono text-[10px] text-muted-foreground">{r}</span>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] text-muted-foreground">Conf <span className={color}>{marketRegime.score}%</span></span>
            <span className={cn("font-mono text-[10px] font-semibold", riskColor)}>RISK {riskLevel}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// ─── GOOD vs BAD Trade Comparison ─────────────────────────────────────────────

function parseDuration(d: string): number {
  const h = d.match(/(\d+)h/)
  const m = d.match(/(\d+)m/)
  return (h ? +h[1] * 60 : 0) + (m ? +m[1] : 0)
}

function formatMins(mins: number): string {
  if (mins < 60) return `${Math.round(mins)}m`
  return `${Math.floor(mins / 60)}h ${Math.round(mins % 60)}m`
}

function GoodBadComparison() {
  const trades = useTradingStore((s) => s.trades)
  const good = trades.filter((t) => t.win)
  const bad  = trades.filter((t) => !t.win)

  const avgRet  = (ts: Trade[]) => ts.length ? (ts.reduce((s, t) => s + t.pnlPct, 0) / ts.length) : null
  const avgHold = (ts: Trade[]) => {
    if (!ts.length) return null
    return ts.reduce((s, t) => s + parseDuration(t.duration), 0) / ts.length
  }
  const topExit = (ts: Trade[]) => {
    if (!ts.length) return '—'
    const cnt: Record<string, number> = {}
    ts.forEach((t) => { cnt[t.exitTag] = (cnt[t.exitTag] ?? 0) + 1 })
    return Object.entries(cnt).sort((a, b) => b[1] - a[1])[0][0].replace('_', ' ')
  }

  const gRet  = avgRet(good);   const bRet  = avgRet(bad)
  const gHold = avgHold(good);  const bHold = avgHold(bad)
  const gExit = topExit(good);  const bExit = topExit(bad)

  return (
    <Card className="shrink-0 border-border bg-card py-1 gap-0">
      <CardHeader className="px-2 py-0 pb-0.5">
        <CardTitle className="flex items-center gap-1.5 font-mono text-[12px] font-medium uppercase tracking-wider text-muted-foreground">
          <GitCompare className="h-3 w-3" />
          WIN vs LOSS
          <span className="ml-auto flex items-center gap-1">
            <ThumbsUp className="h-2.5 w-2.5 text-success" />
            <span className="font-mono text-[11px] text-success">{good.length}</span>
            <span className="text-muted-foreground mx-0.5">/</span>
            <ThumbsDown className="h-2.5 w-2.5 text-destructive" />
            <span className="font-mono text-[11px] text-destructive">{bad.length}</span>
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="px-2 py-0">
        {trades.length === 0 ? (
          <div className="py-2 text-center font-mono text-[11px] text-muted-foreground">체결 대기 중</div>
        ) : (
          <div className="flex flex-col gap-1">
            {/* Column headers */}
            <div className="grid grid-cols-3 gap-1 font-mono text-[10px] uppercase text-muted-foreground">
              <span></span>
              <span className="text-center text-success">WIN</span>
              <span className="text-center text-destructive">LOSS</span>
            </div>

            {/* Avg Return */}
            <div className="grid grid-cols-3 items-center gap-1 rounded bg-muted/20 px-1.5 py-1 font-mono text-[11px]">
              <span className="text-muted-foreground">평균 수익</span>
              <span className="text-center font-semibold text-success">
                {gRet !== null ? `+${gRet.toFixed(2)}%` : '—'}
              </span>
              <span className="text-center font-semibold text-destructive">
                {bRet !== null ? `${bRet.toFixed(2)}%` : '—'}
              </span>
            </div>

            {/* Avg Hold */}
            <div className="grid grid-cols-3 items-center gap-1 rounded bg-muted/20 px-1.5 py-1 font-mono text-[11px]">
              <span className="text-muted-foreground">평균 보유</span>
              <span className="text-center text-success">{gHold !== null ? formatMins(gHold) : '—'}</span>
              <span className="text-center text-destructive">{bHold !== null ? formatMins(bHold) : '—'}</span>
            </div>

            {/* Exit reason */}
            <div className="grid grid-cols-3 items-center gap-1 rounded bg-muted/20 px-1.5 py-1 font-mono text-[11px]">
              <span className="text-muted-foreground">주요 출구</span>
              <span className="text-center text-success text-[10px]">{gExit}</span>
              <span className="text-center text-destructive text-[10px]">{bExit}</span>
            </div>

            {/* Insight */}
            {gRet !== null && bRet !== null && (
              <div className="mt-0.5 rounded bg-muted/20 px-1.5 py-1 font-mono text-[10px] text-muted-foreground leading-tight">
                {gRet > Math.abs(bRet)
                  ? `WIN 평균 수익이 LOSS의 ${(gRet / Math.abs(bRet)).toFixed(1)}배`
                  : `LOSS 관리 필요 — 손절 평균 ${Math.abs(bRet).toFixed(2)}%`
                }
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Position Cards ────────────────────────────────────────────────────────────

function holdTime(mins: number): string {
  if (mins < 60) return `${mins}m`
  const h = Math.floor(mins / 60)
  const m = mins % 60
  return m > 0 ? `${h}h ${m}m` : `${h}h`
}

function positionSignal(p: { strategy: string; chochGrade: string }): string {
  const parts: string[] = []
  if (p.chochGrade === 'A' || p.chochGrade === 'B') parts.push(`CHoCH-${p.chochGrade}`)
  const strat = p.strategy.toUpperCase()
  if (strat.includes('SMC'))   parts.push('Sweep')
  if (strat.includes('MOM') || strat.includes('MOMENTUM')) parts.push('Momentum')
  if (strat.includes('TRD') || strat.includes('TREND'))    parts.push('Trend Align')
  if (strat.includes('MRV'))   parts.push('Reversal')
  return parts.length > 0 ? parts.join(' + ') : strat
}

function PositionCards() {
  const positions = useTradingStore((s) => s.positions)
  const openPnl   = positions.reduce((s, p) => s + p.pnl, 0)
  const totalExp  = positions.reduce((s, p) => s + p.currentPrice * p.quantity, 0)

  return (
    <div className="flex flex-col gap-2">
      {/* Summary header */}
      <div className="flex items-center justify-between rounded-md border border-border bg-card px-2 py-1.5">
        <div className="flex items-center gap-1.5">
          <Layers className="h-3 w-3 text-muted-foreground" />
          <span className="font-mono text-[11px] uppercase text-muted-foreground tracking-wider">POSITIONS</span>
          <span className={cn("font-mono text-[13px] font-semibold", positions.length > 0 ? "text-foreground" : "text-muted-foreground")}>
            {positions.length}
          </span>
        </div>
        <div className="flex items-center gap-3 font-mono text-[11px]">
          <span className="text-muted-foreground">EXPO {totalExp.toLocaleString()}원</span>
          <span className={cn("font-semibold", openPnl >= 0 ? "text-success" : "text-destructive")}>
            {openPnl >= 0 ? "+" : ""}{openPnl.toLocaleString()}원
          </span>
        </div>
      </div>

      {positions.length === 0 && (
        <div className="rounded-md border border-border bg-card py-4 text-center font-mono text-[12px] text-muted-foreground">
          포지션 없음
        </div>
      )}

      {positions.map((p) => {
        const pnlColor = p.pnl >= 0 ? "text-success" : "text-destructive"
        const pnlBg    = p.pnl >= 0 ? "border-success/25 bg-success/5" : "border-destructive/25 bg-destructive/5"
        const signal   = positionSignal(p)
        const size     = (p.entryPrice * p.quantity).toLocaleString()

        return (
          <div key={p.symbol} className={cn("flex flex-col gap-1.5 rounded-md border px-2 py-2", pnlBg)}>

            {/* Header: symbol + direction */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <span className="font-mono text-[13px] font-bold text-foreground">{p.symbol}</span>
                <span className="font-mono text-[10px] text-muted-foreground truncate max-w-[60px]">{p.name}</span>
              </div>
              <Badge className="bg-success/20 text-success px-1.5 py-0 font-mono text-[10px] font-bold">
                ▲ LONG
              </Badge>
            </div>

            {/* Strategy + Entry Reason */}
            <div className="flex items-center gap-1.5">
              <Badge className="bg-muted/50 px-1 py-0 font-mono text-[9px] text-muted-foreground uppercase">
                {p.strategy}
              </Badge>
            </div>
            <div className="flex items-center gap-1 rounded bg-muted/15 px-1.5 py-0.5">
              <span className="font-mono text-[9px] text-muted-foreground uppercase tracking-wider shrink-0">진입 이유</span>
              <span className="font-mono text-[10px] font-medium text-foreground/80">{signal}</span>
            </div>

            {/* Entry → Current */}
            <div className="flex items-center justify-between rounded bg-muted/20 px-1.5 py-1">
              <div className="flex flex-col">
                <span className="font-mono text-[9px] text-muted-foreground">ENTRY</span>
                <span className="font-mono text-[12px] font-medium text-foreground">{p.entryPrice.toLocaleString()}</span>
              </div>
              <span className="font-mono text-[11px] text-muted-foreground">→</span>
              <div className="flex flex-col items-end">
                <span className="font-mono text-[9px] text-muted-foreground">CURRENT</span>
                <span className={cn("font-mono text-[12px] font-semibold", pnlColor)}>{p.currentPrice.toLocaleString()}</span>
              </div>
              <span className={cn("font-mono text-[13px] font-bold ml-1", pnlColor)}>
                {p.pnlPct >= 0 ? "+" : ""}{p.pnlPct.toFixed(2)}%
              </span>
            </div>

            {/* TP / SL */}
            <div className="grid grid-cols-2 gap-1">
              <div className="flex items-center justify-between rounded bg-success/10 px-1.5 py-0.5">
                <span className="font-mono text-[9px] text-success/70">TP</span>
                <span className="font-mono text-[11px] font-semibold text-success">{p.tp.toLocaleString()}</span>
              </div>
              <div className="flex items-center justify-between rounded bg-destructive/10 px-1.5 py-0.5">
                <span className="font-mono text-[9px] text-destructive/70">SL</span>
                <span className="font-mono text-[11px] font-semibold text-destructive">{p.sl.toLocaleString()}</span>
              </div>
            </div>

            {/* Footer: size + hold + P&L */}
            <div className="flex items-center justify-between font-mono text-[11px]">
              <div className="flex items-center gap-2 text-muted-foreground">
                <span>{p.quantity}주 · {size}원</span>
                <span>{holdTime(p.holdMinutes)}</span>
              </div>
              <span className={cn("font-semibold", pnlColor)}>
                {p.pnl >= 0 ? "+" : ""}{p.pnl.toLocaleString()}원
              </span>
            </div>

          </div>
        )
      })}
    </div>
  )
}

// ─── Risk Metrics ─────────────────────────────────────────────────────────────

function RiskMetrics() {
  const trades     = useTradingStore((s) => s.trades)
  const riskMetrics = useTradingStore((s) => s.riskMetrics)

  const wins   = trades.filter((t) => t.win)
  const losses = trades.filter((t) => !t.win)
  const winRate = trades.length > 0 ? Math.round((wins.length / trades.length) * 100) : 0
  const avgWin  = wins.length > 0   ? wins.reduce((s, t) => s + t.pnlPct, 0)   / wins.length   : 0
  const avgLoss = losses.length > 0 ? Math.abs(losses.reduce((s, t) => s + t.pnlPct, 0) / losses.length) : 0
  const rr      = avgLoss > 0 ? (avgWin / avgLoss).toFixed(2) : '—'
  const mddM    = riskMetrics.find((m) => /mdd|drawdown/i.test(m.label))

  const recent3 = trades.slice(-3)
  const recent3W = recent3.filter((t) => t.win).length
  const recent3L = recent3.length - recent3W
  const recentStreak = recent3.length > 0 ? `최근 ${recent3.length}건: ${recent3W}승 ${recent3L}패` : null

  const metrics = [
    {
      label: 'WIN%',
      value: `${winRate}%`,
      status: winRate >= 55 ? 'ok' : winRate >= 40 ? 'warn' : 'danger',
      sub: recentStreak ?? `${wins.length}/${trades.length}`,
    },
    {
      label: 'R:R',
      value: rr === '—' ? '—' : `1:${rr}`,
      status: rr !== '—' && +rr >= 1.5 ? 'ok' : rr !== '—' && +rr >= 1 ? 'warn' : 'danger',
      sub: trades.length > 0 ? `avg` : '—',
    },
    {
      label: 'MDD',
      value: mddM?.value ?? '—',
      status: mddM?.status ?? 'ok',
      sub: 'max',
    },
  ]

  return (
    <div className="flex items-center gap-1 rounded-md border border-border bg-card px-2 py-1.5">
      <AlertTriangle className="h-3 w-3 shrink-0 text-muted-foreground" />
      <span className="font-mono text-[10px] uppercase text-muted-foreground mr-1">RISK</span>
      <div className="flex flex-1 items-center gap-1">
        {metrics.map(({ label, value, status, sub }) => (
          <div key={label} className={cn(
            "flex flex-1 flex-col rounded px-1.5 py-0.5",
            status === 'ok' ? "bg-success/10" : status === 'warn' ? "bg-warning/10" : "bg-destructive/10"
          )}>
            <div className="flex items-center justify-between">
              <span className="font-mono text-[9px] text-muted-foreground">{label}</span>
              <span className={cn("font-mono text-[13px] font-bold",
                status === 'ok' ? "text-success" : status === 'warn' ? "text-warning" : "text-destructive"
              )}>{value}</span>
            </div>
            {sub && <span className="font-mono text-[9px] text-muted-foreground/70 truncate">{sub}</span>}
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Trade Log ────────────────────────────────────────────────────────────────

function TradeLog() {
  const trades = useTradingStore((s) => s.trades)
  return (
    <Card className="shrink-0 border-border bg-card py-1 gap-0">
      <CardHeader className="px-2 py-0 pb-0.5">
        <CardTitle className="flex items-center justify-between font-mono text-[12px] font-medium uppercase tracking-wider text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <Receipt className="h-3 w-3" />
            TRADE_LOG
          </span>
          <span className="text-foreground">{trades.length}</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex max-h-[280px] flex-col gap-1 overflow-y-auto px-1.5 py-0 [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-muted-foreground/30 [&::-webkit-scrollbar-track]:bg-transparent">
        {trades.length === 0 ? (
          <div className="py-4 text-center font-mono text-[12px] text-muted-foreground">체결 없음</div>
        ) : (
          trades.map((trade) => (
            <div key={trade.id} className={cn(
              "flex flex-col gap-1 rounded-md p-1.5",
              trade.win ? "bg-success/5" : "bg-destructive/5"
            )}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="font-mono text-sm font-semibold">{trade.symbol}</span>
                  {trade.name && <span className="font-mono text-[10px] text-muted-foreground/70 truncate max-w-[70px]">{trade.name}</span>}
                  <Badge className={cn("px-1 py-0 font-mono text-[10px]",
                    trade.win ? "bg-success/20 text-success" : "bg-destructive/20 text-destructive"
                  )}>{trade.win ? "W" : "L"}</Badge>
                  <Badge className="bg-muted px-1 py-0 font-mono text-[10px] text-muted-foreground">{trade.strategy}</Badge>
                </div>
                <div className="flex items-center gap-1">
                  {trade.win ? <ArrowUpRight className="h-3 w-3 text-success" /> : <ArrowDownRight className="h-3 w-3 text-destructive" />}
                  <span className={cn("font-mono text-sm font-semibold", trade.win ? "text-success" : "text-destructive")}>
                    {trade.win ? "+" : ""}{trade.pnlPct.toFixed(2)}%
                  </span>
                </div>
              </div>
              <div className="flex items-center justify-between font-mono text-[11px] text-muted-foreground">
                <span>{trade.time}</span>
                <span>{trade.entryPrice.toLocaleString()} → {trade.exitPrice.toLocaleString()}</span>
                <span>{trade.duration}</span>
              </div>
              <div className="flex items-center justify-between">
                <Badge variant="outline" className="border-border/50 px-1 py-0 font-mono text-[9px] text-muted-foreground">
                  {trade.exitTag}
                </Badge>
                {/* 진입 당시 스코어 미니 표시 */}
                {trade.newsScoreAtEntry !== undefined && (
                  <div className="flex items-center gap-1 font-mono text-[9px] text-muted-foreground">
                    <span>뉴스{trade.newsScoreAtEntry}</span>
                    <span>수급{trade.supplyScoreAtEntry}</span>
                    <span>기술{trade.technicalScoreAtEntry}</span>
                  </div>
                )}
                <span className={cn("font-mono text-[11px] font-medium", trade.win ? "text-success" : "text-destructive")}>
                  {trade.win ? "+" : ""}{trade.pnl.toLocaleString()}원
                </span>
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  )
}

// ─── Strategy Performance ─────────────────────────────────────────────────────

function StrategyPerf() {
  const strategyPerf = useTradingStore((s) => s.strategyPerf)
  return (
    <Card className="shrink-0 border-border bg-card py-1 gap-0">
      <CardHeader className="px-2 py-0 pb-0.5">
        <CardTitle className="flex items-center gap-1.5 font-mono text-[12px] font-medium uppercase tracking-wider text-muted-foreground">
          <GitCompare className="h-3 w-3" />
          STRATEGY_PERF
        </CardTitle>
      </CardHeader>
      <CardContent className="px-2 py-0">
        {strategyPerf.length === 0 ? (
          <div className="py-1 text-center font-mono text-[11px] text-muted-foreground">Loading...</div>
        ) : (
          <div className="flex flex-col gap-1">
            <div className="grid grid-cols-12 gap-1 font-mono text-[10px] uppercase text-muted-foreground">
              <span className="col-span-3">STRAT</span>
              <span className="col-span-3 text-right">WIN%</span>
              <span className="col-span-2 text-right">AVG</span>
              <span className="col-span-2 text-right">SR</span>
              <span className="col-span-2 text-right">#</span>
            </div>
            {strategyPerf.map((s) => (
              <div key={s.code} className="grid grid-cols-12 items-center gap-1 rounded bg-muted/20 px-1 py-1">
                <span className="col-span-3 font-mono text-[12px] font-medium">{s.code}</span>
                <div className="col-span-3 flex items-center justify-end gap-1">
                  <Progress value={s.winRate} className={cn(
                    "h-1 w-6 bg-muted",
                    s.winRate >= 65 ? "[&>div]:bg-success" : s.winRate >= 50 ? "[&>div]:bg-warning" : "[&>div]:bg-destructive"
                  )} />
                  <span className={cn("w-7 text-right font-mono text-[11px]",
                    s.winRate >= 65 ? "text-success" : s.winRate >= 50 ? "text-warning" : "text-destructive"
                  )}>{s.winRate}%</span>
                </div>
                <span className="col-span-2 text-right font-mono text-[11px] text-success">+{s.avgReturn}%</span>
                <span className={cn("col-span-2 text-right font-mono text-[11px]",
                  s.sharpe >= 1.5 ? "text-success" : s.sharpe >= 1 ? "text-warning" : "text-destructive"
                )}>{s.sharpe}</span>
                <span className="col-span-2 text-right font-mono text-[11px] text-muted-foreground">{s.trades}</span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Daily Summary ────────────────────────────────────────────────────────────

function DailySummary() {
  const periodPerf = useTradingStore((s) => s.periodPerf)
  const items = [
    { label: 'TODAY', perf: periodPerf?.today },
    { label: 'WEEK',  perf: periodPerf?.week  },
    { label: 'MONTH', perf: periodPerf?.month },
  ]
  return (
    <div className="grid shrink-0 grid-cols-3 gap-1">
      {items.map(({ label, perf }) => (
        <div key={label} className="flex flex-col items-center rounded-md border border-border bg-card px-2 py-1.5">
          <span className="font-mono text-[10px] uppercase text-muted-foreground">{label}</span>
          {perf ? (
            <>
              <span className={cn("font-mono text-lg font-semibold", perf.pnl >= 0 ? "text-success" : "text-destructive")}>
                {perf.pnl >= 0 ? "+" : ""}{perf.pnl.toLocaleString()}원
              </span>
              <span className={cn("font-mono text-[10px]", perf.pct >= 0 ? "text-success" : "text-destructive")}>
                {perf.pct >= 0 ? "+" : ""}{perf.pct.toFixed(2)}%
              </span>
            </>
          ) : (
            <span className="font-mono text-[11px] text-muted-foreground">—</span>
          )}
        </div>
      ))}
    </div>
  )
}

function fmtWon(won: number): string {
  return won.toLocaleString() + '원'
}

function AccountCard() {
  const account = useTradingStore((s) => s.account)

  if (!account) return (
    <div className="shrink-0 rounded-md border border-border bg-card px-3 py-2 font-mono text-[12px] text-muted-foreground text-center">
      Loading...
    </div>
  )

  return (
    <div className="shrink-0 rounded-md border border-border bg-card px-3 py-2 flex flex-col gap-1.5">
      {/* 헤더 라벨 */}
      <div className="flex items-center gap-1.5">
        <Wallet className="h-3 w-3 text-muted-foreground" />
        <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Account</span>
      </div>

      {/* 총자산 크게 */}
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-[11px] text-muted-foreground">총자산</span>
        <span className="font-mono text-[20px] font-bold text-foreground leading-none">{fmtWon(account.totalAssets)}</span>
      </div>

      {/* 예수금 / 보유평가 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1">
          <span className="font-mono text-[11px] text-muted-foreground">예수금</span>
          <span className="font-mono text-[14px] font-semibold text-foreground">{fmtWon(account.deposit)}</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="font-mono text-[11px] text-muted-foreground">보유</span>
          <span className="font-mono text-[14px] font-semibold text-foreground">{fmtWon(account.holdingValue)}</span>
        </div>
      </div>

      {/* 일손익 / 주간손익 */}
      <div className="flex items-center justify-between border-t border-border/40 pt-1">
        {[
          { label: '일', value: account.dailyPnl },
          { label: '주', value: account.weeklyPnl },
        ].map(({ label, value }) => (
          <div key={label} className="flex items-center gap-1">
            <span className="font-mono text-[11px] text-muted-foreground">{label}손익</span>
            <span className={cn('font-mono text-[14px] font-bold',
              value > 0 ? 'text-success' : value < 0 ? 'text-destructive' : 'text-muted-foreground'
            )}>
              {value >= 0 ? '+' : ''}{fmtWon(value)}
            </span>
          </div>
        ))}
        {account.consecutiveLosses >= 2 && (
          <span className="font-mono text-[11px] font-bold text-destructive">연패{account.consecutiveLosses}</span>
        )}
      </div>
    </div>
  )
}

// ─── Main ─────────────────────────────────────────────────────────────────────

export function RightPanel() {
  return (
    <aside className="flex w-[20%] min-w-[220px] flex-col gap-2 overflow-y-auto border-l border-border bg-sidebar p-2 [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-muted-foreground/30 [&::-webkit-scrollbar-track]:bg-transparent">
      <TradeBias />
      <AccountCard />
      <PositionCards />
      <RiskMetrics />
      <DateRangePicker />
      <TradeLog />
      <GoodBadComparison />
      <StrategyPerf />
      <DailySummary />
    </aside>
  )
}
