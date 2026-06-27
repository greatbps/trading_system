"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { cn } from "@/lib/utils"
import { TrendingUp, BarChart3, Filter } from "lucide-react"
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

function scoreGrade(score: number): string {
  if (score >= 85) return 'A+'
  if (score >= 75) return 'A'
  if (score >= 65) return 'B+'
  if (score >= 55) return 'B'
  if (score >= 45) return 'C'
  return 'D'
}

function keySignal(c: Candidate): string {
  if (c.volRatio >= 2.5) return `VOL ${c.volRatio.toFixed(1)}x`
  if (c.changePct >= 2)  return `MOM +${c.changePct.toFixed(1)}%`
  if (c.chochGrade === 'A') return `CHoCH-A Break`
  const topPass = c.conditions.find((cond) => cond.pass)
  return topPass ? topPass.label : c.strategy
}

function CandidateRow({ candidate, selected, onSelect, rank }: {
  candidate: Candidate
  selected: boolean
  onSelect: () => void
  rank: number
}) {
  const { symbol, name, changePct, sparkline, entryScore, chochGrade, conditions, nearMiss, confidence } = candidate
  const passCount = conditions.filter((c) => c.pass).length
  const isTop3 = rank < 3

  // Decision signal
  const decision: 'PASS' | 'WATCH' | 'BLOCK' =
    entryScore >= 70 && passCount >= Math.ceil(conditions.length * 0.6) ? 'PASS' :
    entryScore < 50 || passCount < Math.ceil(conditions.length * 0.35) ? 'BLOCK' :
    'WATCH'

  const isStrong = decision === 'PASS' && confidence >= 80
  const signal   = keySignal(candidate)

  return (
    <button
      onClick={onSelect}
      className={cn(
        "flex flex-col rounded-md text-left transition-all w-full",
        isTop3 ? "gap-0.5 p-1" : "gap-0 px-1 py-0.5 opacity-60",
        selected ? "bg-accent"
          : isTop3 && decision === 'PASS' ? "border border-success/35 bg-success/5 hover:bg-success/10"
          : isTop3 && decision === 'BLOCK' ? "border border-destructive/25 bg-destructive/5 hover:bg-destructive/10"
          : isTop3 ? "border border-warning/25 hover:bg-muted/50"
          : "hover:bg-muted/40",
        !isTop3 && nearMiss && "border-l-2 border-warning"
      )}
    >
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1">
          {isTop3 && (
            <span className="font-mono text-[9px] text-muted-foreground/40">#{rank + 1}</span>
          )}
          <span className={cn("font-mono font-semibold", isTop3 ? "text-[12px]" : "text-[11px]")}>{symbol}</span>
          <span className="font-mono text-[10px] text-muted-foreground truncate max-w-[45px]">{name}</span>
          <span className={cn("font-mono text-[10px]", changePct >= 0 ? "text-success" : "text-destructive")}>
            {changePct >= 0 ? "+" : ""}{changePct.toFixed(2)}%
          </span>
        </div>
        <div className="flex items-center gap-1">
          <Badge className={cn(
            "px-1.5 py-0 font-mono text-[10px] font-bold",
            decision === 'PASS' && isStrong ? "bg-success text-success-foreground" :
            decision === 'PASS'             ? "bg-success/80 text-success-foreground" :
            decision === 'BLOCK'            ? "bg-destructive text-destructive-foreground" :
                                              "bg-warning/20 text-warning border border-warning/30"
          )}>
            {decision === 'PASS' ? (isStrong ? `★ ${scoreGrade(entryScore)}` : scoreGrade(entryScore)) : decision}
          </Badge>
          {isTop3 && <Sparkline data={sparkline} />}
        </div>
      </div>

      {/* Top-3: key signal label */}
      {isTop3 && (
        <div className="flex items-center gap-1">
          <span className={cn(
            "font-mono text-[10px] font-medium",
            decision === 'PASS' ? "text-success/80" : decision === 'BLOCK' ? "text-destructive/70" : "text-warning/80"
          )}>{signal}</span>
          {confidence > 0 && (
            <span className="font-mono text-[9px] text-muted-foreground ml-auto">conf {confidence}%</span>
          )}
        </div>
      )}

      {/* Top-3: full detail */}
      {isTop3 && (
        <>
          <div className="grid grid-cols-4 gap-0.5">
            {conditions.map((cond) => (
              <div key={cond.key} className={cn(
                "flex flex-col items-center rounded px-0.5 py-[1px]",
                cond.pass ? "bg-success/10" : "bg-destructive/10"
              )}>
                <span className="font-mono text-[9px] uppercase text-muted-foreground truncate w-full text-center leading-tight">
                  {cond.label.slice(0, 5)}
                </span>
                <span className={cn("font-mono text-[10px] leading-tight",
                  cond.pass ? "text-success" : "text-destructive"
                )}>{cond.value}</span>
              </div>
            ))}
          </div>

          <div className="flex items-center gap-1.5">
            <div className="flex flex-1 items-center gap-1">
              <span className="font-mono text-[10px] text-muted-foreground">ENT</span>
              <Progress value={entryScore} className={cn(
                "h-1 flex-1 bg-muted",
                entryScore >= 75 ? "[&>div]:bg-success" : entryScore >= 50 ? "[&>div]:bg-warning" : "[&>div]:bg-destructive"
              )} />
              <span className={cn("w-5 font-mono text-[10px]",
                entryScore >= 75 ? "text-success" : entryScore >= 50 ? "text-warning" : "text-destructive"
              )}>{entryScore}</span>
            </div>
            <div className="flex items-center gap-1">
              <Badge className={cn("px-1 py-0 font-mono text-[10px]",
                chochGrade === 'A' ? "bg-success/20 text-success"
                  : chochGrade === 'B' ? "bg-warning/20 text-warning"
                  : "bg-muted text-muted-foreground"
              )}>{chochGrade}</Badge>
              <span className="font-mono text-[10px] text-muted-foreground">{passCount}/{conditions.length}</span>
            </div>
          </div>
        </>
      )}

      {/* Non-top-3: compact score line */}
      {!isTop3 && (
        <div className="flex items-center gap-1.5">
          <span className={cn("font-mono text-[10px]",
            entryScore >= 75 ? "text-success" : entryScore >= 50 ? "text-warning" : "text-destructive"
          )}>{entryScore}</span>
          <Badge className={cn("px-1 py-0 font-mono text-[9px]",
            chochGrade === 'A' ? "bg-success/20 text-success" : "bg-warning/20 text-warning"
          )}>{chochGrade}</Badge>
          <span className="font-mono text-[10px] text-muted-foreground">{passCount}/{conditions.length}</span>
        </div>
      )}
    </button>
  )
}

export function LeftSidebar() {
  const { candidates, selectedSymbol, selectSymbol, marketRegime, filterStats, decisionLog } = useTradingStore()

  const f1 = filterStats.find((f) => f.stage === 1)
  const f2 = filterStats.find((f) => f.stage === 2)
  const scanCount = f1?.total ?? 0
  const passCount = f2?.passed ?? 0
  const execCount = decisionLog.filter((e) => e.type === 'EXEC').length

  const regime = marketRegime

  return (
    <aside className="flex h-full w-[23%] min-w-[200px] flex-col gap-2 overflow-hidden border-r border-border bg-sidebar p-2">
      {/* Market Regime */}
      <Card className="shrink-0 border-border bg-card py-2 gap-0">
        <CardHeader className="px-2 py-0 pb-1">
          <CardTitle className="flex items-center gap-1.5 font-mono text-[12px] font-medium uppercase tracking-wider text-muted-foreground">
            <BarChart3 className="h-3 w-3" />
            MKT_REGIME
          </CardTitle>
        </CardHeader>
        <CardContent className="px-2 py-0">
          {regime ? (
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1">
                  {(['TREND', 'SIDEWAYS', 'VOLATILE'] as const).map((r) => (
                    <Badge key={r} className={cn(
                      "px-1 py-0 font-mono text-[10px] font-medium",
                      regime.regime === r
                        ? r === 'TREND' ? "bg-success/20 text-success"
                          : r === 'VOLATILE' ? "bg-destructive/20 text-destructive"
                          : "bg-warning/20 text-warning"
                        : "bg-muted text-muted-foreground"
                    )}>
                      {r === 'SIDEWAYS' ? 'SIDE' : r}
                    </Badge>
                  ))}
                </div>
                <div className="flex items-center gap-2">
                  {[
                    { label: 'SCR', value: regime.score, color: 'text-success' },
                    { label: 'VIX', value: regime.vix,   color: 'text-warning'  },
                    { label: 'ADX', value: regime.adx,   color: 'text-success'  },
                  ].map(({ label, value, color }) => (
                    <div key={label} className="flex items-center gap-0.5">
                      <span className="font-mono text-[9px] text-muted-foreground">{label}</span>
                      <span className={cn("font-mono text-[12px] font-semibold", color)}>{value}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-4 gap-1">
                {[
                  { label: 'TRD', value: regime.trend    },
                  { label: 'MOM', value: regime.momentum },
                  { label: 'VOL', value: regime.volume   },
                  { label: 'RSK', value: regime.risk     },
                ].map(({ label, value }) => (
                  <div key={label} className="flex flex-col items-center rounded bg-muted/20 px-1 py-0.5">
                    <span className="font-mono text-[9px] text-muted-foreground">{label}</span>
                    <span className={cn("font-mono text-[11px] font-medium",
                      value >= 60 ? "text-success" : value >= 40 ? "text-warning" : "text-destructive"
                    )}>{value}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="py-1 text-center font-mono text-[12px] text-muted-foreground">Loading...</div>
          )}
        </CardContent>
      </Card>

      {/* Candidate List */}
      <Card className="flex flex-col flex-1 overflow-hidden border-border bg-card py-2 gap-0">
        <CardHeader className="px-2 py-0 pb-1.5">
          <CardTitle className="flex items-center justify-between font-mono text-[12px] font-medium uppercase tracking-wider text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <TrendingUp className="h-3 w-3" />
              CANDIDATES
            </span>
            <span className="text-foreground">{candidates.length}</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-1 min-h-0 flex-col gap-1 overflow-y-auto px-1.5 py-0 [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-muted-foreground/30 [&::-webkit-scrollbar-track]:bg-transparent">
          {candidates.length === 0 ? (
            <div className="py-4 text-center font-mono text-[12px] text-muted-foreground">Scanning...</div>
          ) : (
            candidates.map((c, idx) => (
              <CandidateRow
                key={c.symbol}
                candidate={c}
                rank={idx}
                selected={selectedSymbol === c.symbol}
                onSelect={() => selectSymbol(c.symbol)}
              />
            ))
          )}
        </CardContent>
      </Card>

      {/* Signal Funnel: SCAN › PASS › EXEC */}
      <div className="shrink-0 flex items-center justify-around rounded-md border border-border bg-card px-3 py-1.5">
        <div className="flex flex-col items-center">
          <span className="font-mono text-[9px] uppercase text-muted-foreground">SCAN</span>
          <span className="font-mono text-lg font-semibold text-foreground">{scanCount}</span>
        </div>
        <span className="font-mono text-[14px] text-muted-foreground/40">›</span>
        <div className="flex flex-col items-center">
          <span className="font-mono text-[9px] uppercase text-muted-foreground">PASS</span>
          <span className="font-mono text-lg font-semibold text-chart-4">{passCount}</span>
        </div>
        <span className="font-mono text-[14px] text-muted-foreground/40">›</span>
        <div className="flex flex-col items-center">
          <span className="font-mono text-[9px] uppercase text-muted-foreground">EXEC</span>
          <span className="font-mono text-lg font-semibold text-success">{execCount}</span>
        </div>
      </div>
    </aside>
  )
}
