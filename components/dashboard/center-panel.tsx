"use client"

import { useState, useEffect, useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { cn } from "@/lib/utils"
import {
  CandlestickChart, Target, Activity,
  ArrowRight, TrendingUp, TrendingDown,
  Newspaper, BarChart2, BrainCircuit,
} from "lucide-react"
import { useTradingStore } from "@/store/trading"
import type { DecisionEvent, NewsItem, SimilarPattern } from "@/src/types/trading"

// ─── SVG Candlestick ──────────────────────────────────────────────────────────

interface Candle { o: number; h: number; l: number; c: number; time?: string }

function CandlestickSvg({ candles, entryIndex, sl, tp }: {
  candles: Candle[]
  entryIndex?: number
  sl?: number
  tp?: number
}) {
  if (!candles.length) return (
    <div className="flex h-[150px] items-center justify-center font-mono text-[13px] text-muted-foreground">
      좌측에서 후보 종목을 선택하세요
    </div>
  )

  const H = 132, LW = 36, XH = 14  // XH = x-axis label area height
  const prices = candles.flatMap((c) => [c.l, c.h])
  const minP = Math.min(...prices, ...(sl ? [sl * 0.999] : []))
  const maxP = Math.max(...prices, ...(tp ? [tp * 1.001] : []))
  const range = maxP - minP || 1
  const sy = (p: number) => H - ((p - minP) / range) * H

  const cw = 7, gap = 2
  const ox = LW + 4
  const W = Math.max(430, ox + candles.length * (cw + gap) + 24)
  const totalH = H + XH

  // Pick time labels every ~8 bars
  const timeLabelIndices: number[] = []
  candles.forEach((c, i) => {
    if (c.time && (i === 0 || i % 8 === 0 || i === candles.length - 1)) {
      timeLabelIndices.push(i)
    }
  })

  return (
    <svg className="h-[160px] w-full" viewBox={`0 0 ${W} ${totalH}`} preserveAspectRatio="none">
      {/* Y-axis grid + price labels */}
      {[0, 0.25, 0.5, 0.75, 1].map((t, i) => {
        const p = minP + range * t
        const y = sy(p)
        return (
          <g key={i}>
            <line x1={ox} y1={y} x2={ox + (cw+gap)*candles.length} y2={y}
              stroke="var(--border)" strokeWidth="0.4" strokeDasharray="2,4" />
            <text x={2} y={y + 3} fill="var(--muted-foreground)" fontSize="7" fontFamily="monospace">
              {p >= 1000 ? (p/1000).toFixed(0)+'K' : p.toFixed(0)}
            </text>
          </g>
        )
      })}

      {/* TP / SL zones (filled) + entry line */}
      {(() => {
        const entryPrice = entryIndex != null ? candles[entryIndex]?.c : undefined
        const zoneW = (cw + gap) * candles.length
        return (
          <>
            {tp && entryPrice && (
              <rect x={ox} y={sy(tp)} width={zoneW} height={Math.max(sy(entryPrice) - sy(tp), 0)}
                fill="var(--success)" opacity="0.07" />
            )}
            {sl && entryPrice && (
              <rect x={ox} y={sy(entryPrice)} width={zoneW} height={Math.max(sy(sl) - sy(entryPrice), 0)}
                fill="var(--destructive)" opacity="0.07" />
            )}
            {entryPrice && (
              <line x1={ox} y1={sy(entryPrice)} x2={ox + zoneW} y2={sy(entryPrice)}
                stroke="var(--success)" strokeWidth="1.5" opacity="0.85" />
            )}
          </>
        )
      })()}

      {/* SL / TP dashed lines + labels */}
      {sl && <line x1={ox} y1={sy(sl)} x2={ox+(cw+gap)*candles.length} y2={sy(sl)} stroke="var(--destructive)" strokeWidth="1" strokeDasharray="4,2" opacity="0.8" />}
      {tp && <line x1={ox} y1={sy(tp)} x2={ox+(cw+gap)*candles.length} y2={sy(tp)} stroke="var(--success)" strokeWidth="1" strokeDasharray="4,2" opacity="0.8" />}
      {sl && <text x={ox+(cw+gap)*candles.length+2} y={sy(sl)+3} fill="var(--destructive)" fontSize="7" fontFamily="monospace">SL</text>}
      {tp && <text x={ox+(cw+gap)*candles.length+2} y={sy(tp)+3} fill="var(--success)" fontSize="7" fontFamily="monospace">TP</text>}

      {/* Candles */}
      {candles.map((c, i) => {
        const x = ox + i * (cw + gap)
        const bull = c.c >= c.o
        const color = bull ? "var(--success)" : "var(--destructive)"
        const bodyTop = sy(Math.max(c.o, c.c))
        const bodyBot = sy(Math.min(c.o, c.c))
        const cx = x + cw / 2
        return (
          <g key={i}>
            <line x1={cx} y1={sy(c.h)} x2={cx} y2={sy(c.l)} stroke={color} strokeWidth="1" />
            <rect x={x} y={bodyTop} width={cw} height={Math.max(bodyBot - bodyTop, 1.5)} fill={color} rx="0.5" />
            {i === entryIndex && (
              <polygon points={`${cx},${sy(c.l)+8} ${x-2},${sy(c.l)+16} ${x+cw+2},${sy(c.l)+16}`} fill="var(--success)" opacity="0.9" />
            )}
          </g>
        )
      })}

      {/* X-axis baseline */}
      <line x1={ox} y1={H + 1} x2={ox + (cw+gap)*candles.length} y2={H + 1} stroke="var(--border)" strokeWidth="0.5" />

      {/* X-axis time labels */}
      {timeLabelIndices.map((i) => {
        const x = ox + i * (cw + gap) + cw / 2
        const label = candles[i].time ?? ''
        return (
          <g key={i}>
            <line x1={x} y1={H + 1} x2={x} y2={H + 4} stroke="var(--border)" strokeWidth="0.5" />
            <text
              x={x} y={H + XH - 1}
              fill="var(--muted-foreground)" fontSize="7" fontFamily="monospace"
              textAnchor="middle"
            >{label}</text>
          </g>
        )
      })}
    </svg>
  )
}

// ─── Chart Panel ──────────────────────────────────────────────────────────────

function ChartPanel() {
  const detail     = useTradingStore((s) => s.selectedDetail)
  const symbol     = useTradingStore((s) => s.selectedSymbol)
  const candidates = useTradingStore((s) => s.candidates)
  const candidate  = candidates.find((c) => c.symbol === symbol)

  const candles = (detail?.ohlcv ?? []).map((c) => ({ o: c.open, h: c.high, l: c.low, c: c.close, time: c.time }))
  const last = candles[candles.length - 1]
  const prev = candles[candles.length - 2]
  const changePct = last && prev ? ((last.c - prev.c) / prev.c) * 100 : 0
  const positive  = changePct >= 0

  return (
    <Card className="shrink-0 border-border bg-card py-1 gap-0">
      <CardHeader className="px-3 py-0 pb-0.5">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 font-mono text-[12px] font-medium uppercase tracking-wider text-muted-foreground">
            <CandlestickChart className="h-3 w-3" />
            {symbol ? `${symbol}` : "CHART"}
            {candidate && <span className="font-mono text-[12px] normal-case text-foreground">{candidate.name}</span>}
            <span className="text-muted-foreground">5M</span>
          </CardTitle>
          {last && (
            <div className="flex items-center gap-3 font-mono text-[12px]">
              <span className="font-semibold text-lg text-foreground">{last.c.toLocaleString()}원</span>
              <Badge className={cn("px-1.5 py-0 text-[11px]", positive ? "bg-success/20 text-success" : "bg-destructive/20 text-destructive")}>
                {positive ? <TrendingUp className="mr-0.5 inline h-2.5 w-2.5" /> : <TrendingDown className="mr-0.5 inline h-2.5 w-2.5" />}
                {positive ? "+" : ""}{changePct.toFixed(2)}%
              </Badge>
              {candidate && (
                <>
                  <span className="text-muted-foreground">VOL {candidate.volRatio.toFixed(1)}x</span>
                  <span className="text-muted-foreground">RSI {candidate.rsi}</span>
                </>
              )}
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="px-3 py-0">
        {/* Decision overlay */}
        {detail && last && candidate && (() => {
          const score = detail.totalScore
          const action: 'LONG' | 'WATCH' | 'NO TRADE' = score >= 75 ? 'LONG' : score >= 55 ? 'WATCH' : 'NO TRADE'
          const conf = candidate.confidence
          const confLevel = conf >= 75 ? 'HIGH' : conf >= 50 ? 'MED' : 'LOW'
          const confColor = confLevel === 'HIGH' ? 'text-success' : confLevel === 'MED' ? 'text-warning' : 'text-destructive'
          const tpPct = ((detail.tp - last.c) / last.c * 100).toFixed(1)
          const slPct = ((last.c - detail.sl) / last.c * 100).toFixed(1)
          const actionColor = action === 'LONG' ? 'text-success border-success/30 bg-success/5'
            : action === 'WATCH' ? 'text-warning border-warning/30 bg-warning/5'
            : 'text-muted-foreground border-border bg-muted/10'
          return (
            <div className={cn("mb-1.5 flex items-center justify-between rounded border px-2 py-1 font-mono", actionColor)}>
              <div className="flex items-center gap-2">
                <span className="text-[14px] font-bold">
                  {action === 'LONG' ? '▲ LONG' : action === 'WATCH' ? '◆ WATCH' : '🚫 NO TRADE'}
                </span>
                <span className="text-[11px] text-muted-foreground">
                  Confidence: <span className={confColor}>{confLevel}</span>
                  <span className="opacity-60"> ({conf}%)</span>
                </span>
                <span className="text-[11px] text-muted-foreground">Score {score}</span>
              </div>
              <div className="flex items-center gap-3 text-[11px]">
                {action !== 'NO TRADE' && (
                  <>
                    <span className="text-muted-foreground">Entry <span className="text-foreground font-medium">{last.c.toLocaleString()}</span></span>
                    <span className="text-success">TP +{tpPct}%</span>
                    <span className="text-destructive">SL -{slPct}%</span>
                    <span className="text-muted-foreground">R:R 1:{detail.rrRatio.toFixed(1)}</span>
                  </>
                )}
                {action === 'NO TRADE' && (
                  <span className="text-muted-foreground text-[10px]">진입 조건 미충족</span>
                )}
              </div>
            </div>
          )
        })()}

        <CandlestickSvg candles={candles} entryIndex={detail?.entryIndex} sl={detail?.sl} tp={detail?.tp} />

      </CardContent>
    </Card>
  )
}

// ─── Research Card ────────────────────────────────────────────────────────────

function SentimentDot({ s }: { s: NewsItem['sentiment'] }) {
  return (
    <span className={cn(
      "inline-block h-2 w-2 shrink-0 rounded-full mt-0.5",
      s === 'positive' ? "bg-success" : s === 'negative' ? "bg-destructive" : "bg-muted-foreground"
    )} />
  )
}

function SupplyBar({ label, value, max = 250 }: { label: string; value: number; max?: number }) {
  const pct = Math.min(Math.abs(value) / max * 100, 100)
  const positive = value >= 0
  return (
    <div className="flex items-center gap-1.5">
      <span className="w-8 font-mono text-[10px] text-muted-foreground">{label}</span>
      <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full", positive ? "bg-success" : "bg-destructive")}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={cn("w-14 text-right font-mono text-[11px]", positive ? "text-success" : "text-destructive")}>
        {positive ? "+" : ""}{value}억
      </span>
    </div>
  )
}

function PatternRow({ p }: { p: SimilarPattern }) {
  const positive = p.returnPct >= 0
  return (
    <div className="flex items-center justify-between font-mono text-[11px]">
      <span className="text-muted-foreground">{p.date}</span>
      <Badge className="bg-muted/30 px-1 py-0 text-[9px] text-muted-foreground">{p.regime}</Badge>
      <span className="text-muted-foreground">{p.holdDays}일</span>
      <span className={cn("font-medium w-12 text-right", positive ? "text-success" : "text-destructive")}>
        {positive ? "+" : ""}{p.returnPct.toFixed(1)}%
      </span>
    </div>
  )
}

function ResearchCard() {
  const detail   = useTradingStore((s) => s.selectedDetail)
  const symbol   = useTradingStore((s) => s.selectedSymbol)
  const candidates = useTradingStore((s) => s.candidates)
  const candidate  = candidates.find((c) => c.symbol === symbol)

  if (!detail || !symbol) {
    return (
      <Card className="flex-1 border-border bg-card py-1 gap-0">
        <CardHeader className="px-3 py-0 pb-0.5">
          <CardTitle className="flex items-center gap-1.5 font-mono text-[12px] font-medium uppercase tracking-wider text-muted-foreground">
            <Target className="h-3 w-3" />
            ANALYSIS
          </CardTitle>
        </CardHeader>
        <CardContent className="px-3 py-0">
          <div className="flex flex-col items-center gap-2 py-10 text-center">
            <Target className="h-8 w-8 text-muted-foreground/30" />
            <span className="font-mono text-[12px] text-muted-foreground">후보 종목을 선택하면<br />종합 분석이 표시됩니다</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  const decision = detail.totalScore >= 75 ? "BUY"
    : detail.totalScore >= 55 ? "WATCH" : "SKIP"
  const decisionColor =
    decision === "BUY"   ? "bg-success text-success-foreground" :
    decision === "WATCH" ? "bg-warning text-warning-foreground" :
    "bg-muted text-muted-foreground"

  const avgPattern = detail.similarPatterns.length > 0
    ? detail.similarPatterns.reduce((s, p) => s + p.returnPct, 0) / detail.similarPatterns.length
    : 0

  return (
    <Card className="flex-1 overflow-hidden border-border bg-card py-1 gap-0">
      <CardHeader className="px-3 py-0 pb-0.5">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-1.5 font-mono text-[12px] font-medium uppercase tracking-wider text-muted-foreground">
            <Target className="h-3 w-3" />
            ANALYSIS
          </CardTitle>
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-[12px] font-semibold text-foreground">{symbol}</span>
            <Badge className={cn("px-1.5 py-0 font-mono text-[11px] font-bold", decisionColor)}>
              {decision}
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="h-[calc(100%-34px)] overflow-y-auto px-3 py-0 flex flex-col gap-2.5 [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-muted-foreground/30 [&::-webkit-scrollbar-track]:bg-transparent">

        {/* ── 0. Analysis Summary ─────────────────────────────────── */}
        {(() => {
          const sc = detail.totalScore
          const passedScores = detail.scores.filter((s) => s.score >= 65).length
          const totalScores  = detail.scores.length
          const weak = detail.scores.filter((s) => s.score < 50).map((s) => s.name).join('/')
          const summaryText = sc >= 75
            ? `진입 조건 충족 (${passedScores}/${totalScores} 항목 통과) → 진입 권장`
            : sc >= 55
            ? `일부 조건 미충족 (${weak || '기술'} 약함) → 관망 권장`
            : `기술적 조건 부족 (${weak || 'Volume/Trend'} 약함) → 진입 비추천`
          const bgColor = sc >= 75 ? 'bg-success/8 border-success/20' : sc >= 55 ? 'bg-warning/8 border-warning/20' : 'bg-muted/20 border-border'
          const textColor = sc >= 75 ? 'text-success' : sc >= 55 ? 'text-warning' : 'text-muted-foreground'
          return (
            <div className={cn("rounded border px-2 py-1.5", bgColor)}>
              <span className="font-mono text-[9px] uppercase text-muted-foreground/70 tracking-wider">ANALYSIS SUMMARY</span>
              <div className={cn("font-mono text-[11px] font-medium leading-snug mt-0.5", textColor)}>
                → {summaryText}
              </div>
            </div>
          )
        })()}

        {/* ── 1. Score Breakdown ──────────────────────────────────── */}
        <div className="flex flex-col gap-1">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[10px] uppercase text-muted-foreground tracking-wider">종합 점수</span>
            <span className="font-mono text-2xl font-bold text-success">{detail.totalScore}</span>
          </div>
          {detail.scores.map((s) => (
            <div key={s.name} className="flex items-center gap-1.5">
              <span className="w-12 font-mono text-[11px] text-muted-foreground">{s.name}</span>
              <Progress
                value={s.score}
                className={cn(
                  "h-1.5 flex-1 bg-muted",
                  s.score >= 70 ? "[&>div]:bg-success" : s.score >= 50 ? "[&>div]:bg-warning" : "[&>div]:bg-destructive"
                )}
              />
              <span className={cn("w-7 text-right font-mono text-[11px]",
                s.score >= 70 ? "text-success" : s.score >= 50 ? "text-warning" : "text-destructive"
              )}>{s.score}</span>
            </div>
          ))}
          {candidate && (
            <div className="flex items-center gap-2 pt-0.5">
              <Badge className={cn("px-1 py-0 font-mono text-[9px]",
                candidate.chochGrade === 'A' ? "bg-success/20 text-success" : "bg-warning/20 text-warning"
              )}>CHoCH-{candidate.chochGrade}</Badge>
              <span className="font-mono text-[11px] text-muted-foreground">VOL {candidate.volRatio}x</span>
              <span className="font-mono text-[11px] text-muted-foreground">RSI {candidate.rsi}</span>
              <Badge className="bg-muted px-1 py-0 font-mono text-[9px] text-muted-foreground ml-auto">
                {candidate.filterStage === 2 ? '2차통과' : '1차통과'}
              </Badge>
            </div>
          )}
        </div>

        {/* ── 2. SL / TP ─────────────────────────────────────────── */}
        <div className="grid grid-cols-3 gap-1 border-t border-border pt-2">
          {[
            { label: 'SL', value: detail.sl.toLocaleString(), color: 'text-destructive' },
            { label: 'TP', value: detail.tp.toLocaleString(), color: 'text-success' },
            { label: 'R:R', value: `1:${detail.rrRatio.toFixed(1)}`, color: 'text-foreground' },
          ].map(({ label, value, color }) => (
            <div key={label} className="flex flex-col items-center rounded bg-muted/20 px-1 py-1">
              <span className="font-mono text-[9px] text-muted-foreground">{label}</span>
              <span className={cn("font-mono text-[12px] font-semibold", color)}>{value}</span>
            </div>
          ))}
        </div>

        {/* ── 3. 뉴스 분석 ────────────────────────────────────────── */}
        <div className="border-t border-border pt-2">
          <div className="flex items-center gap-1.5 mb-1.5">
            <Newspaper className="h-3 w-3 text-muted-foreground" />
            <span className="font-mono text-[11px] uppercase text-muted-foreground tracking-wider">뉴스 재료</span>
            <span className={cn(
              "ml-auto font-mono text-[12px] font-semibold",
              candidate && candidate.newsScore >= 7 ? "text-success" : "text-warning"
            )}>{candidate?.newsScore.toFixed(1)}</span>
          </div>
          <div className="flex flex-col gap-1">
            {detail.newsItems.map((item, i) => (
              <div key={i} className="flex items-start gap-1.5">
                <SentimentDot s={item.sentiment} />
                <div className="flex-1 min-w-0">
                  <div className="font-mono text-[11px] text-foreground/80 leading-tight">{item.text}</div>
                  <div className="flex items-center gap-1 mt-0.5">
                    <span className="font-mono text-[9px] text-muted-foreground">{item.source}</span>
                    <span className="font-mono text-[9px] text-muted-foreground">{item.time}</span>
                    <span className={cn(
                      "ml-auto font-mono text-[10px]",
                      item.impact > 0 ? "text-success" : item.impact < 0 ? "text-destructive" : "text-muted-foreground"
                    )}>{item.impact > 0 ? "+" : ""}{item.impact.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ── 4. 수급 분석 ────────────────────────────────────────── */}
        <div className="border-t border-border pt-2">
          <div className="flex items-center gap-1.5 mb-1.5">
            <BarChart2 className="h-3 w-3 text-muted-foreground" />
            <span className="font-mono text-[11px] uppercase text-muted-foreground tracking-wider">수급 분석</span>
            {detail.supplyFlow.days > 0 && (
              <Badge className="ml-auto bg-success/10 px-1 py-0 font-mono text-[9px] text-success">
                {detail.supplyFlow.days}일 연속 매수
              </Badge>
            )}
          </div>
          <div className="flex flex-col gap-1">
            <SupplyBar label="외국인" value={detail.supplyFlow.foreign} />
            <SupplyBar label="기관" value={detail.supplyFlow.institution} />
            <SupplyBar label="프로그램" value={detail.supplyFlow.program} />
            <SupplyBar label="개인" value={detail.supplyFlow.retailNet} />
          </div>
          <div className="mt-1 font-mono text-[11px] text-muted-foreground leading-tight">
            {detail.supplySummary}
          </div>
        </div>

        {/* ── 5. AI 기대수익 + 유사 패턴 ─────────────────────────── */}
        <div className="border-t border-border pt-2">
          <div className="flex items-center gap-1.5 mb-1.5">
            <BrainCircuit className="h-3 w-3 text-muted-foreground" />
            <span className="font-mono text-[11px] uppercase text-muted-foreground tracking-wider">AI 분석</span>
            <span className={cn(
              "ml-auto font-mono text-[13px] font-bold",
              detail.aiExpectation >= 1.5 ? "text-success" : "text-warning"
            )}>+{detail.aiExpectation.toFixed(1)}% 기대</span>
          </div>
          <div className="flex flex-col gap-1 mb-1.5">
            <span className="font-mono text-[10px] text-muted-foreground">과거 유사 패턴 (평균 {avgPattern >= 0 ? "+" : ""}{avgPattern.toFixed(1)}%)</span>
            {detail.similarPatterns.map((p, i) => <PatternRow key={i} p={p} />)}
          </div>
          <div className="font-mono text-[11px] text-muted-foreground leading-tight">
            {detail.technicalSummary}
          </div>
        </div>

      </CardContent>
    </Card>
  )
}

// ─── Signal Feed ─────────────────────────────────────────────────────────────

const EVENT_COLOR: Record<string, string> = {
  EXEC:   "text-success",
  FILTER: "text-warning",
  BLOCK:  "text-destructive",
  SCORE:  "text-chart-5",
  SCAN:   "text-muted-foreground",
  TRAIL:  "text-success",
  SYSTEM: "text-muted-foreground",
}

function isHighPriority(event: DecisionEvent): boolean {
  return event.type === 'EXEC' || event.type === 'BLOCK' ||
    event.resultClass === 'exec' || event.resultClass === 'block' ||
    (event.type === 'FILTER' && event.resultClass === 'pass')
}

function SignalFeed() {
  const decisionLog = useTradingStore((s) => s.decisionLog)
  const [sinceUpdate, setSinceUpdate] = useState(0)
  const lastKeyRef = useRef('')

  const execCount   = decisionLog.filter((e) => e.type === 'EXEC').length
  const passCount   = decisionLog.filter((e) => e.resultClass === 'pass' || e.resultClass === 'exec').length
  const rejectCount = decisionLog.filter((e) => e.resultClass === 'reject' || e.resultClass === 'block').length

  useEffect(() => {
    const key = decisionLog.map((e) => e.id).join(',')
    if (key !== lastKeyRef.current) {
      lastKeyRef.current = key
      setSinceUpdate(0)
    }
  }, [decisionLog])

  useEffect(() => {
    const iv = setInterval(() => setSinceUpdate((s) => s + 1), 1000)
    return () => clearInterval(iv)
  }, [])

  return (
    <Card className="flex-1 overflow-hidden border-border bg-card py-1 gap-0">
      <CardHeader className="px-3 py-0 pb-0.5">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-1.5 font-mono text-[12px] font-medium uppercase tracking-wider text-muted-foreground">
            <Activity className="h-3 w-3" />
            SIGNAL_FEED
            <span className={cn(
              "font-mono text-[10px] tabular-nums",
              sinceUpdate <= 3 ? "text-success" : "text-muted-foreground/50"
            )}>{sinceUpdate}s ago</span>
          </CardTitle>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1">
              <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-success" />
              <span className="font-mono text-[11px] text-success">{passCount} pass</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="h-1.5 w-1.5 rounded-full bg-destructive" />
              <span className="font-mono text-[11px] text-destructive">{rejectCount} reject</span>
            </div>
            <span className="font-mono text-[11px] text-chart-4">{execCount} exec</span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="relative h-[calc(100%-36px)] overflow-y-auto px-3 py-0 [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-muted-foreground/30 [&::-webkit-scrollbar-track]:bg-transparent">
        <div className="absolute left-[18px] top-1 h-[calc(100%-4px)] w-px bg-border/40" />
        {decisionLog.length === 0 ? (
          <div className="py-6 text-center font-mono text-[12px] text-muted-foreground">시그널 대기 중...</div>
        ) : (
          <div className="flex flex-col gap-0">
            {decisionLog.map((event: DecisionEvent) => (
              <div key={event.id} className={cn(
                "group relative flex items-start gap-2.5 py-1",
                isHighPriority(event) ? "rounded px-1 -mx-1 bg-muted/20" : ""
              )}>
                <div className={cn(
                  "relative z-10 mt-1.5 h-2 w-2 shrink-0 rounded-full",
                  event.resultClass === 'exec' || event.resultClass === 'pass' ? "bg-success"
                  : event.resultClass === 'reject' || event.resultClass === 'block' ? "bg-destructive"
                  : event.resultClass === 'score' ? "bg-chart-5"
                  : "bg-muted-foreground"
                )} />
                <div className="flex flex-1 min-w-0 flex-col">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[11px] text-muted-foreground whitespace-nowrap">{event.time}</span>
                    <span className={cn("font-mono text-[11px] font-medium", EVENT_COLOR[event.type] ?? "text-muted-foreground")}>{event.type}</span>
                    {event.symbol && event.symbol !== '——' && (
                      <span className="font-mono text-[11px] font-semibold text-foreground">{event.symbol}</span>
                    )}
                    {event.symbolName && (
                      <span className="font-mono text-[10px] text-muted-foreground/70 truncate max-w-[80px]">{event.symbolName}</span>
                    )}
                    <span className={cn("ml-auto shrink-0 font-mono text-[11px]",
                      event.resultClass === 'exec' || event.resultClass === 'pass' ? "text-success"
                      : event.resultClass === 'reject' || event.resultClass === 'block' ? "text-destructive"
                      : "text-muted-foreground"
                    )}>{event.result}</span>
                  </div>
                  <div className="font-mono text-[11px] text-foreground/70 truncate">
                    {event.event} — {event.params}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Bottom Stats ─────────────────────────────────────────────────────────────

function BottomStats() {
  const decisionLog = useTradingStore((s) => s.decisionLog)
  const positions   = useTradingStore((s) => s.positions)
  const trades      = useTradingStore((s) => s.trades)
  const periodPerf  = useTradingStore((s) => s.periodPerf)
  const filterStats = useTradingStore((s) => s.filterStats)

  const executed  = decisionLog.filter((e) => e.type === 'EXEC').length
  const winCount  = trades.filter((t) => t.win).length
  const winRate   = trades.length > 0 ? Math.round((winCount / trades.length) * 100) : 0
  const todayPnl  = periodPerf?.today.pnl ?? 0
  const todayPct  = periodPerf?.today.pct ?? 0
  const openPnl   = positions.reduce((s, p) => s + p.pnl, 0)

  const f1 = filterStats.find((f) => f.stage === 1)
  const f2 = filterStats.find((f) => f.stage === 2)
  const scanCount = f1?.total ?? 0
  const passCount = f2?.passed ?? 0

  const todayColor = todayPnl >= 0 ? "text-success" : "text-destructive"
  const openColor  = openPnl  >= 0 ? "text-success" : "text-destructive"
  const winColor   = winRate  >= 55 ? "text-success" : winRate >= 40 ? "text-warning" : "text-destructive"

  return (
    <div className="grid shrink-0 grid-cols-3 gap-2">

      {/* A — FUNNEL */}
      <div className="flex items-center justify-around rounded-md border border-border bg-card px-3 py-1.5">
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
          <span className="font-mono text-lg font-semibold text-success">{executed}</span>
        </div>
      </div>

      {/* B — TODAY P&L (most prominent) + WIN% */}
      {(() => {
        const bestPnl = trades.length > 0 ? Math.max(...trades.map((t) => t.pnl)) : 0
        return (
          <div className="flex items-center justify-around rounded-md border border-border bg-card px-3 py-1.5">
            <div className="flex flex-col items-center">
              <span className="font-mono text-[9px] uppercase text-muted-foreground">WIN%</span>
              <span className={cn("font-mono text-lg font-semibold", winColor)}>{winRate}%</span>
              <span className="font-mono text-[9px] text-muted-foreground">{winCount}/{trades.length}</span>
            </div>
            <div className="h-8 w-px bg-border/40" />
            <div className="flex flex-col items-center">
              <span className="font-mono text-[9px] uppercase text-muted-foreground">TODAY P&L</span>
              <span className={cn("font-mono text-2xl font-bold leading-none", todayColor)}>
                {todayPnl >= 0 ? "+" : ""}{todayPnl.toLocaleString()}원
              </span>
              <span className={cn("font-mono text-[10px]", todayColor)}>
                {todayPct >= 0 ? "+" : ""}{todayPct.toFixed(2)}%
              </span>
              {trades.length > 0 && (
                <span className="font-mono text-[9px] text-muted-foreground mt-0.5">
                  {trades.length}건 · Best +{bestPnl.toLocaleString()}원
                </span>
              )}
            </div>
          </div>
        )
      })()}

      {/* C — OPEN P&L + POS */}
      <div className="flex items-center justify-around rounded-md border border-border bg-card px-3 py-1.5">
        <div className="flex flex-col items-center">
          <span className="font-mono text-[9px] uppercase text-muted-foreground">OPEN P&L</span>
          <span className={cn("font-mono text-lg font-semibold", openColor)}>
            {openPnl >= 0 ? "+" : ""}{openPnl.toLocaleString()}원
          </span>
        </div>
        <div className="h-8 w-px bg-border/40" />
        <div className="flex flex-col items-center">
          <span className="font-mono text-[9px] uppercase text-muted-foreground">POS</span>
          <span className={cn("font-mono text-lg font-semibold", positions.length > 0 ? "text-foreground" : "text-muted-foreground")}>
            {positions.length}
          </span>
          <span className="font-mono text-[9px] text-muted-foreground">포지션</span>
        </div>
      </div>

    </div>
  )
}

// ─── Main ─────────────────────────────────────────────────────────────────────

function WinPnlStats() {
  const trades     = useTradingStore((s) => s.trades)
  const periodPerf = useTradingStore((s) => s.periodPerf)
  const positions  = useTradingStore((s) => s.positions)

  const winCount  = trades.filter((t) => t.win).length
  const winRate   = trades.length > 0 ? Math.round((winCount / trades.length) * 100) : 0
  const todayPnl  = periodPerf?.today.pnl ?? 0
  const todayPct  = periodPerf?.today.pct ?? 0
  const openPnl   = positions.reduce((s, p) => s + p.pnl, 0)
  const bestPnl   = trades.length > 0 ? Math.max(...trades.map((t) => t.pnl)) : 0

  const todayColor = todayPnl >= 0 ? "text-success" : "text-destructive"
  const openColor  = openPnl  >= 0 ? "text-success" : "text-destructive"
  const winColor   = winRate  >= 55 ? "text-success" : winRate >= 40 ? "text-warning" : "text-destructive"

  return (
    <div className="shrink-0 flex flex-col gap-1 rounded-md border border-border bg-card px-3 py-2">
      {/* WIN% */}
      <div className="flex items-center justify-between">
        <span className="font-mono text-[9px] uppercase text-muted-foreground">WIN%</span>
        <div className="flex items-center gap-1">
          <span className={cn("font-mono text-[13px] font-bold", winColor)}>{winRate}%</span>
          <span className="font-mono text-[9px] text-muted-foreground">{winCount}/{trades.length}</span>
        </div>
      </div>
      {/* TODAY P&L */}
      <div className="flex items-center justify-between">
        <span className="font-mono text-[9px] uppercase text-muted-foreground">TODAY P&L</span>
        <div className="flex items-center gap-1">
          <span className={cn("font-mono text-[15px] font-bold leading-none", todayColor)}>
            {todayPnl >= 0 ? "+" : ""}{todayPnl.toLocaleString()}원
          </span>
          <span className={cn("font-mono text-[10px]", todayColor)}>
            ({todayPct >= 0 ? "+" : ""}{todayPct.toFixed(2)}%)
          </span>
        </div>
      </div>
      {/* OPEN P&L */}
      <div className="flex items-center justify-between">
        <span className="font-mono text-[9px] uppercase text-muted-foreground">OPEN P&L</span>
        <span className={cn("font-mono text-[13px] font-semibold", openColor)}>
          {openPnl >= 0 ? "+" : ""}{openPnl.toLocaleString()}원
        </span>
      </div>
      {trades.length > 0 && (
        <div className="font-mono text-[9px] text-muted-foreground text-right">
          Best +{bestPnl.toLocaleString()}원
        </div>
      )}
    </div>
  )
}

export function CenterPanel() {
  return (
    <main className="flex flex-1 flex-col gap-2 overflow-hidden bg-background p-2">
      <div className="flex flex-1 gap-2 overflow-hidden">
        {/* Left: Chart on top, SignalFeed below */}
        <div className="flex flex-1 flex-col gap-2 overflow-hidden">
          <ChartPanel />
          <SignalFeed />
        </div>
        {/* Right: ResearchCard + WIN/P&L below */}
        <div className="flex w-[38%] min-w-[280px] flex-col gap-2 overflow-hidden">
          <ResearchCard />
          <WinPnlStats />
        </div>
      </div>
    </main>
  )
}
