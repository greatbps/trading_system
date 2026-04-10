"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { cn } from "@/lib/utils"
import {
  Receipt, GitCompare, Layers, AlertTriangle,
  ArrowUpRight, ArrowDownRight, Filter,
  ThumbsUp, ThumbsDown,
} from "lucide-react"
import { useTradingStore } from "@/store/trading"
import type { Trade } from "@/src/types/trading"

// ─── Filter Pass Rate ─────────────────────────────────────────────────────────

function FilterStats() {
  const filterStats = useTradingStore((s) => s.filterStats)
  const f1 = filterStats.find((f) => f.stage === 1)
  const f2 = filterStats.find((f) => f.stage === 2)

  return (
    <Card className="shrink-0 border-border bg-card py-2">
      <CardHeader className="px-2 py-0 pb-1.5">
        <CardTitle className="flex items-center gap-1.5 font-mono text-[12px] font-medium uppercase tracking-wider text-muted-foreground">
          <Filter className="h-3 w-3" />
          FILTER_PIPELINE
        </CardTitle>
      </CardHeader>
      <CardContent className="px-2 py-0">
        {[f1, f2].map((f, i) => {
          if (!f) return null
          const pct = Math.round((f.passed / f.total) * 100)
          return (
            <div key={i} className="mb-2">
              <div className="flex items-center justify-between mb-0.5">
                <span className="font-mono text-[11px] text-muted-foreground">{f.stage === 1 ? '1차 스캔' : '2차 정밀'}</span>
                <span className="font-mono text-[11px] text-foreground">{f.passed} / {f.total}</span>
                <span className={cn(
                  "font-mono text-[11px] font-semibold",
                  pct >= 20 ? "text-warning" : "text-success"
                )}>{pct}%</span>
              </div>
              <div className="relative h-2 rounded-full bg-muted overflow-hidden">
                <div
                  className={cn("h-full rounded-full", f.stage === 2 ? "bg-success" : "bg-chart-4")}
                  style={{ width: `${Math.max(pct, 2)}%` }}
                />
              </div>
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}

// ─── GOOD vs BAD Trade Comparison ─────────────────────────────────────────────

function GoodBadComparison() {
  const trades = useTradingStore((s) => s.trades)
  const good = trades.filter((t) => t.win)
  const bad  = trades.filter((t) => !t.win)

  const avgScore = (items: Trade[], key: keyof Trade) => {
    if (!items.length) return 0
    return +(items.reduce((s, t) => s + ((t[key] as number) ?? 0), 0) / items.length).toFixed(1)
  }

  const metrics = [
    {
      label: '뉴스 점수',
      good: avgScore(good, 'newsScoreAtEntry'),
      bad:  avgScore(bad,  'newsScoreAtEntry'),
      max: 10,
    },
    {
      label: '수급 점수',
      good: avgScore(good, 'supplyScoreAtEntry'),
      bad:  avgScore(bad,  'supplyScoreAtEntry'),
      max: 10,
    },
    {
      label: '기술 점수',
      good: avgScore(good, 'technicalScoreAtEntry'),
      bad:  avgScore(bad,  'technicalScoreAtEntry'),
      max: 10,
    },
  ]

  return (
    <Card className="shrink-0 border-border bg-card py-2">
      <CardHeader className="px-2 py-0 pb-1.5">
        <CardTitle className="flex items-center gap-1.5 font-mono text-[12px] font-medium uppercase tracking-wider text-muted-foreground">
          <GitCompare className="h-3 w-3" />
          GOOD vs BAD
          <span className="ml-auto flex items-center gap-1">
            <ThumbsUp className="h-2.5 w-2.5 text-success" />
            <span className="text-success">{good.length}</span>
            <span className="text-muted-foreground mx-0.5">/</span>
            <ThumbsDown className="h-2.5 w-2.5 text-destructive" />
            <span className="text-destructive">{bad.length}</span>
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="px-2 py-0">
        <div className="mb-1 grid grid-cols-3 gap-1 font-mono text-[10px] text-muted-foreground uppercase">
          <span>지표</span>
          <span className="text-center text-success">WIN</span>
          <span className="text-center text-destructive">LOSS</span>
        </div>
        {metrics.map(({ label, good: g, bad: b, max }) => (
          <div key={label} className="mb-1.5">
            <div className="grid grid-cols-3 items-center gap-1 font-mono text-[11px]">
              <span className="text-muted-foreground">{label}</span>
              <span className="text-center text-success font-semibold">{g}</span>
              <span className="text-center text-destructive font-semibold">{b}</span>
            </div>
            <div className="grid grid-cols-2 gap-0.5 mt-0.5">
              <Progress value={(g / max) * 100} className="h-1 bg-muted [&>div]:bg-success" />
              <Progress value={(b / max) * 100} className="h-1 bg-muted [&>div]:bg-destructive" />
            </div>
          </div>
        ))}
        {trades.length > 0 && (
          <div className="mt-1 rounded bg-muted/20 px-1.5 py-1 font-mono text-[10px] text-muted-foreground leading-tight">
            {metrics[0].good > metrics[0].bad
              ? `💡 WIN 트레이드는 뉴스 점수가 평균 ${(metrics[0].good - metrics[0].bad).toFixed(1)}pt 높음`
              : `⚠️ LOSS 트레이드 패턴: 수급 점수 ${metrics[1].bad} (WIN: ${metrics[1].good})`
            }
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Position Summary ──────────────────────────────────────────────────────────

function PositionSummary() {
  const positions = useTradingStore((s) => s.positions)
  const openPnl   = positions.reduce((s, p) => s + p.pnl, 0)
  const totalExp  = positions.reduce((s, p) => s + p.currentPrice * p.quantity, 0)
  const riskPct   = Math.min(Math.round((totalExp / 50_000_000) * 100), 100)

  return (
    <Card className="shrink-0 border-border bg-card py-2">
      <CardHeader className="px-2 py-0 pb-1.5">
        <CardTitle className="flex items-center gap-1.5 font-mono text-[12px] font-medium uppercase tracking-wider text-muted-foreground">
          <Layers className="h-3 w-3" />
          POSITIONS
        </CardTitle>
      </CardHeader>
      <CardContent className="px-2 py-0">
        <div className="grid grid-cols-4 gap-1 mb-2">
          {[
            { label: 'OPEN', value: String(positions.length), color: 'text-foreground' },
            { label: 'EXPO', value: `${(totalExp/1_000_000).toFixed(1)}M`, color: 'text-foreground' },
            { label: 'P&L',  value: `${openPnl>=0?'+':''}${(openPnl/10000).toFixed(0)}만`, color: openPnl>=0?'text-success':'text-destructive' },
            { label: 'RISK', value: `${riskPct}%`, color: riskPct > 70 ? 'text-destructive' : 'text-warning' },
          ].map(({ label, value, color }) => (
            <div key={label} className="flex flex-col items-center rounded bg-muted/20 px-1 py-1">
              <span className={cn("font-mono text-lg font-semibold", color)}>{value}</span>
              <span className="font-mono text-[9px] uppercase text-muted-foreground">{label}</span>
            </div>
          ))}
        </div>
        {positions.map((p) => (
          <div key={p.symbol} className="flex items-center justify-between rounded bg-muted/20 px-1.5 py-1 mb-1">
            <div className="flex items-center gap-1.5">
              <span className="font-mono text-[12px] font-semibold">{p.symbol}</span>
              <Badge className="bg-muted px-1 py-0 font-mono text-[9px] text-muted-foreground">{p.strategy}</Badge>
              <Badge className={cn("px-1 py-0 font-mono text-[9px]",
                p.chochGrade === 'A' ? "bg-success/20 text-success" : "bg-warning/20 text-warning"
              )}>{p.chochGrade}</Badge>
            </div>
            <div className="flex items-center gap-2 font-mono text-[11px]">
              <span className="text-muted-foreground">{p.holdMinutes}m</span>
              <span className={cn(p.pnl >= 0 ? "text-success" : "text-destructive")}>
                {p.pnl >= 0 ? "+" : ""}{p.pnlPct.toFixed(1)}%
              </span>
            </div>
          </div>
        ))}
        {positions.length === 0 && (
          <div className="py-1 text-center font-mono text-[11px] text-muted-foreground">포지션 없음</div>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Risk Metrics ─────────────────────────────────────────────────────────────

function RiskMetrics() {
  const riskMetrics = useTradingStore((s) => s.riskMetrics)
  return (
    <Card className="shrink-0 border-border bg-card py-2">
      <CardHeader className="px-2 py-0 pb-1.5">
        <CardTitle className="flex items-center gap-1.5 font-mono text-[12px] font-medium uppercase tracking-wider text-muted-foreground">
          <AlertTriangle className="h-3 w-3" />
          RISK_METRICS
        </CardTitle>
      </CardHeader>
      <CardContent className="px-2 py-0">
        {riskMetrics.length === 0 ? (
          <div className="py-1 text-center font-mono text-[11px] text-muted-foreground">Loading...</div>
        ) : (
          <div className="grid grid-cols-3 gap-1">
            {riskMetrics.map((metric) => (
              <div
                key={metric.label}
                title={metric.description}
                className={cn(
                  "flex flex-col items-center rounded px-1 py-1",
                  metric.status === "ok" ? "bg-success/10" : metric.status === "warn" ? "bg-warning/10" : "bg-destructive/10"
                )}
              >
                <span className="font-mono text-[10px] uppercase text-muted-foreground">{metric.label}</span>
                <span className={cn("font-mono text-sm font-semibold",
                  metric.status === "ok" ? "text-success" : metric.status === "warn" ? "text-warning" : "text-destructive"
                )}>{metric.value}</span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Trade Log ────────────────────────────────────────────────────────────────

function TradeLog() {
  const trades = useTradingStore((s) => s.trades)
  return (
    <Card className="flex-1 overflow-hidden border-border bg-card py-2">
      <CardHeader className="px-2 py-0 pb-1.5">
        <CardTitle className="flex items-center justify-between font-mono text-[12px] font-medium uppercase tracking-wider text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <Receipt className="h-3 w-3" />
            TRADE_LOG
          </span>
          <span className="text-foreground">{trades.length}</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex h-[calc(100%-28px)] flex-col gap-1 overflow-y-auto px-1.5 py-0">
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
                  {trade.win ? "+" : ""}{(trade.pnl/10000).toFixed(1)}만
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
    <Card className="shrink-0 border-border bg-card py-2">
      <CardHeader className="px-2 py-0 pb-1.5">
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
                {perf.pnl >= 0 ? "+" : ""}{(perf.pnl/10000).toFixed(0)}만
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

// ─── Main ─────────────────────────────────────────────────────────────────────

export function RightPanel() {
  return (
    <aside className="flex w-[26%] min-w-[280px] flex-col gap-2 overflow-y-auto border-l border-border bg-sidebar p-2">
      <FilterStats />
      <PositionSummary />
      <RiskMetrics />
      <GoodBadComparison />
      <TradeLog />
      <StrategyPerf />
      <DailySummary />
    </aside>
  )
}
