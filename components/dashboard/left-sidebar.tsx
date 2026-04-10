"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { cn } from "@/lib/utils"
import {
  TrendingUp, BarChart3, Activity,
  AlertTriangle, CheckCircle2, XCircle,
} from "lucide-react"
import { useTradingStore } from "@/store/trading"
import type { Candidate } from "@/src/types/trading"

function Sparkline({ data }: { data: number[] }) {
  const max = Math.max(...data)
  const min = Math.min(...data)
  const range = max - min || 1
  const W = 48, H = 16
  const pts = data
    .map((v, i) => `${(i / (data.length - 1)) * W},${H - ((v - min) / range) * H}`)
    .join(" ")
  const positive = data[data.length - 1] > data[0]
  return (
    <svg className="shrink-0" width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
      <polyline
        points={pts}
        fill="none"
        stroke={positive ? "var(--success)" : "var(--destructive)"}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function CandidateRow({ candidate, selected, onSelect }: {
  candidate: Candidate
  selected: boolean
  onSelect: () => void
}) {
  const { symbol, name, price, changePct, sparkline, entryScore, riskScore, confidence, chochGrade, volRatio, rsi, conditions, nearMiss } = candidate
  const passCount = conditions.filter((c) => c.pass).length

  return (
    <button
      onClick={onSelect}
      className={cn(
        "flex flex-col gap-1 rounded-md p-1.5 text-left transition-colors w-full",
        selected ? "bg-accent" : "hover:bg-muted/50",
        nearMiss && "border-l-2 border-warning"
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span className="font-mono text-sm font-semibold">{symbol}</span>
          <span className="font-mono text-[11px] text-muted-foreground truncate max-w-[60px]">{name}</span>
          <span className={cn(
            "font-mono text-[11px]",
            changePct >= 0 ? "text-success" : "text-destructive"
          )}>
            {changePct >= 0 ? "+" : ""}{changePct.toFixed(2)}%
          </span>
        </div>
        <Sparkline data={sparkline} />
      </div>

      {/* Conditions */}
      <div className="grid grid-cols-4 gap-0.5">
        {conditions.map((cond) => (
          <div
            key={cond.key}
            className={cn(
              "flex flex-col items-center rounded px-0.5 py-0.5",
              cond.pass ? "bg-success/10" : "bg-destructive/10"
            )}
          >
            {cond.pass
              ? <CheckCircle2 className="h-2.5 w-2.5 text-success" />
              : <XCircle className="h-2.5 w-2.5 text-destructive" />}
            <span className="font-mono text-[9px] uppercase text-muted-foreground truncate w-full text-center">
              {cond.label.slice(0, 5)}
            </span>
            <span className={cn(
              "font-mono text-[10px]",
              cond.pass ? "text-success" : "text-destructive"
            )}>
              {cond.value}
            </span>
          </div>
        ))}
      </div>

      {/* Scores */}
      <div className="flex items-center gap-2">
        <div className="flex flex-1 items-center gap-1">
          <span className="font-mono text-[10px] text-muted-foreground">ENT</span>
          <Progress
            value={entryScore}
            className={cn(
              "h-1 flex-1 bg-muted",
              entryScore >= 75 ? "[&>div]:bg-success" : entryScore >= 50 ? "[&>div]:bg-warning" : "[&>div]:bg-destructive"
            )}
          />
          <span className={cn(
            "w-5 font-mono text-[11px]",
            entryScore >= 75 ? "text-success" : entryScore >= 50 ? "text-warning" : "text-destructive"
          )}>{entryScore}</span>
        </div>
        <div className="flex items-center gap-1">
          <Badge className={cn(
            "px-1 py-0 font-mono text-[10px]",
            chochGrade === 'A' ? "bg-success/20 text-success"
              : chochGrade === 'B' ? "bg-warning/20 text-warning"
              : "bg-muted text-muted-foreground"
          )}>
            {chochGrade}
          </Badge>
          <span className="font-mono text-[10px] text-muted-foreground">{passCount}/{conditions.length}</span>
        </div>
      </div>
    </button>
  )
}

export function LeftSidebar() {
  const { candidates, selectedSymbol, selectSymbol, marketRegime, systemHealth } = useTradingStore()

  const health = systemHealth ?? {
    dataFeed:    { status: 'ok' as const, latency: 0 },
    orderRouter: { status: 'ok' as const, latency: 0 },
    riskEngine:  { status: 'ok' as const, latency: 0 },
    signalGen:   { status: 'ok' as const, latency: 0 },
  }

  const healthEntries = [
    { label: 'DATA', ...health.dataFeed },
    { label: 'ORDR', ...health.orderRouter },
    { label: 'RISK', ...health.riskEngine },
    { label: 'SGNL', ...health.signalGen },
  ] as const

  const regime = marketRegime

  return (
    <aside className="flex w-[22%] min-w-[260px] flex-col gap-2 overflow-y-auto border-r border-border bg-sidebar p-2">
      {/* System Health */}
      <Card className="shrink-0 border-border bg-card py-2">
        <CardHeader className="px-2 py-0 pb-1.5">
          <CardTitle className="flex items-center gap-1.5 font-mono text-[12px] font-medium uppercase tracking-wider text-muted-foreground">
            <Activity className="h-3 w-3" />
            SYS_HEALTH
          </CardTitle>
        </CardHeader>
        <CardContent className="px-2 py-0">
          <div className="grid grid-cols-4 gap-1">
            {healthEntries.map((entry) => (
              <div
                key={entry.label}
                className={cn(
                  "flex flex-col items-center rounded px-1 py-1",
                  entry.status === "ok" ? "bg-success/10" : entry.status === "warn" ? "bg-warning/10" : "bg-destructive/10"
                )}
              >
                {entry.status === "ok"
                  ? <CheckCircle2 className="h-3 w-3 text-success" />
                  : <AlertTriangle className={cn("h-3 w-3", entry.status === "warn" ? "text-warning" : "text-destructive")} />}
                <span className="font-mono text-[10px] text-muted-foreground">{entry.label}</span>
                <span className={cn(
                  "font-mono text-[11px]",
                  entry.status === "ok" ? "text-success" : entry.status === "warn" ? "text-warning" : "text-destructive"
                )}>{entry.latency}ms</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Market Regime */}
      <Card className="shrink-0 border-border bg-card py-2">
        <CardHeader className="px-2 py-0 pb-1.5">
          <CardTitle className="flex items-center gap-1.5 font-mono text-[12px] font-medium uppercase tracking-wider text-muted-foreground">
            <BarChart3 className="h-3 w-3" />
            MKT_REGIME
          </CardTitle>
        </CardHeader>
        <CardContent className="px-2 py-0">
          {regime ? (
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-1">
                {(['TREND', 'SIDEWAYS', 'VOLATILE'] as const).map((r) => (
                  <Badge
                    key={r}
                    className={cn(
                      "px-1.5 py-0 font-mono text-[11px] font-medium",
                      regime.regime === r
                        ? r === 'TREND' ? "bg-success/20 text-success"
                          : r === 'VOLATILE' ? "bg-destructive/20 text-destructive"
                          : "bg-warning/20 text-warning"
                        : "bg-muted text-muted-foreground"
                    )}
                  >
                    {r === 'SIDEWAYS' ? 'SIDE' : r}
                  </Badge>
                ))}
              </div>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { label: 'SCORE', value: regime.score, color: 'text-success' },
                  { label: 'VIX',   value: regime.vix,   color: 'text-warning'  },
                  { label: 'ADX',   value: regime.adx,   color: 'text-success'  },
                ].map(({ label, value, color }) => (
                  <div key={label} className="flex flex-col gap-0.5">
                    <span className="font-mono text-[10px] uppercase text-muted-foreground">{label}</span>
                    <span className={cn("font-mono text-lg font-semibold", color)}>{value}</span>
                    <Progress value={Math.min(value, 100)} className={cn(
                      "h-1 bg-muted",
                      color === 'text-success' ? "[&>div]:bg-success" : "[&>div]:bg-warning"
                    )} />
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-4 gap-1 pt-0.5">
                {[
                  { label: 'TRD', value: regime.trend    },
                  { label: 'MOM', value: regime.momentum },
                  { label: 'VOL', value: regime.volume   },
                  { label: 'RSK', value: regime.risk     },
                ].map(({ label, value }) => (
                  <div key={label} className="flex flex-col items-center rounded bg-muted/20 px-1 py-0.5">
                    <span className="font-mono text-[9px] text-muted-foreground">{label}</span>
                    <span className={cn(
                      "font-mono text-[12px] font-medium",
                      value >= 60 ? "text-success" : value >= 40 ? "text-warning" : "text-destructive"
                    )}>{value}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="py-2 text-center font-mono text-[12px] text-muted-foreground">Loading...</div>
          )}
        </CardContent>
      </Card>

      {/* Candidate List */}
      <Card className="flex-1 overflow-hidden border-border bg-card py-2">
        <CardHeader className="px-2 py-0 pb-1.5">
          <CardTitle className="flex items-center justify-between font-mono text-[12px] font-medium uppercase tracking-wider text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <TrendingUp className="h-3 w-3" />
              CANDIDATES
            </span>
            <span className="text-foreground">{candidates.length}</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-1 overflow-y-auto px-1.5 py-0">
          {candidates.length === 0 ? (
            <div className="py-4 text-center font-mono text-[12px] text-muted-foreground">Scanning...</div>
          ) : (
            candidates.map((c) => (
              <CandidateRow
                key={c.symbol}
                candidate={c}
                selected={selectedSymbol === c.symbol}
                onSelect={() => selectSymbol(c.symbol)}
              />
            ))
          )}
        </CardContent>
      </Card>
    </aside>
  )
}
