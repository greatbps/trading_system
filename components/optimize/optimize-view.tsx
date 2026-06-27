"use client"

import { useState, useEffect, useRef, useCallback } from 'react'
import { Play, Square, RotateCcw, Trophy, TrendingUp } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import {
  startOptimize,
  getOptimizeStatus,
  getOptimizeResults,
  cancelOptimize,
  applyOptimize,
} from '@/lib/api'
import type { OptimizeRequest, OptimizeStatus, OptimizeRow, OptimizeResults } from '@/lib/api'

// ─── Types ────────────────────────────────────────────────────────────────────

type JobState = 'idle' | 'running' | 'done' | 'error'
type Mode = 'tp_sl' | 'swing'

// ─── 상수 ─────────────────────────────────────────────────────────────────────

const STRATEGIES = ['B', 'B+HTF', 'B+VOL', 'B+HTF+VOL', 'B+VOL+EMA60']

const TP_PRESETS: Record<Mode, { label: string; values: number[] }[]> = {
  tp_sl: [
    { label: '좁게 (2~4%)',  values: [0.02, 0.03, 0.04] },
    { label: '기본 (2~5%)',  values: [0.02, 0.03, 0.04, 0.05] },
    { label: '넓게 (2~6%)',  values: [0.02, 0.03, 0.04, 0.05, 0.06] },
  ],
  swing: [
    { label: '스윙 짧게 (8~12%)',  values: [0.08, 0.10, 0.12] },
    { label: '스윙 기본 (8~18%)',  values: [0.08, 0.12, 0.18] },
    { label: '스윙 전체 (8~25%)', values: [0.08, 0.12, 0.18, 0.25] },
  ],
}

const SL_PRESETS: Record<Mode, { label: string; values: number[] }[]> = {
  tp_sl: [
    { label: '타이트 (1~2%)', values: [0.01, 0.015, 0.02] },
    { label: '기본 (1~3%)',   values: [0.01, 0.015, 0.02, 0.025, 0.03] },
    { label: '넓게 (1.5~3%)', values: [0.015, 0.02, 0.025, 0.03] },
  ],
  swing: [
    { label: '스윙 타이트 (2~3%)', values: [0.02, 0.03] },
    { label: '스윙 기본 (2~5%)',   values: [0.02, 0.03, 0.05] },
    { label: '스윙 넓게 (2~8%)',   values: [0.02, 0.03, 0.05, 0.08] },
  ],
}

const MIN_HOLD_OPTS   = [8, 16, 24, 48, 72]
const TRAILING_OPTS   = [0.05, 0.08, 0.10, 0.12, 0.15]
const BE_TRIGGER_OPTS = [0.02, 0.03, 0.05]

// ─── 색상 헬퍼 ───────────────────────────────────────────────────────────────

function heatColor(val: number, min: number, max: number): string {
  if (max === min) return 'hsl(200,40%,25%)'
  const t = (val - min) / (max - min)
  if (t < 0.5) return `rgb(180,${Math.round(t * 2 * 180)},30)`
  return `rgb(${Math.round((1 - (t - 0.5) * 2) * 180)},180,30)`
}

// ─── 히트맵 ───────────────────────────────────────────────────────────────────

type SwingAxis = 'hold_trail' | 'tp_trail'

function Heatmap({ rows, mode }: { rows: OptimizeRow[]; mode: Mode }) {
  const [swingAxis, setSwingAxis] = useState<SwingAxis>('hold_trail')

  if (rows.length === 0) return null

  if (mode === 'swing') {
    // ── 스윙 히트맵: 축 전환 가능 ──────────────────────────────────────────

    // 1) hold × trailing: 각 셀 = 해당 조합 중 best score 행
    // 2) TP × trailing:   각 셀 = 해당 조합 중 best score 행
    type CellKey = string
    type CellMap = Map<CellKey, OptimizeRow>

    function buildCellMap(xKey: (r: OptimizeRow) => number, yKey: (r: OptimizeRow) => number): CellMap {
      const m = new Map<CellKey, OptimizeRow>()
      for (const r of rows) {
        const k = `${xKey(r)}_${yKey(r)}`
        const existing = m.get(k)
        if (!existing || r.score > existing.score) m.set(k, r)
      }
      return m
    }

    const isTP = swingAxis === 'tp_trail'
    const xVals = isTP
      ? [...new Set(rows.map(r => r.tp!))].sort((a, b) => a - b)
      : [...new Set(rows.map(r => r.min_hold!))].sort((a, b) => a - b)
    const yVals = [...new Set(rows.map(r => r.trailing!))].sort((a, b) => a - b)

    const cellMap = isTP
      ? buildCellMap(r => r.tp!, r => r.trailing!)
      : buildCellMap(r => r.min_hold!, r => r.trailing!)

    const metric = (r: OptimizeRow) => r.capture_rate ?? r.ret
    const allScores = [...cellMap.values()].map(metric)
    const minS = Math.min(...allScores)
    const maxS = Math.max(...allScores)

    return (
      <div className="space-y-3">
        {/* 축 전환 탭 */}
        <div className="flex gap-2 items-center">
          <span className="text-[10px] font-mono text-muted-foreground">축:</span>
          {(['hold_trail', 'tp_trail'] as SwingAxis[]).map(ax => (
            <button
              key={ax}
              onClick={() => setSwingAxis(ax)}
              className={cn(
                'px-2 py-0.5 rounded text-[10px] font-mono border transition-colors',
                swingAxis === ax
                  ? 'border-accent text-accent bg-accent/10'
                  : 'border-border text-muted-foreground hover:border-foreground'
              )}
            >
              {ax === 'hold_trail' ? '보유봉 × 트레일링' : 'TP × 트레일링 ★'}
            </button>
          ))}
          <span className="text-[10px] font-mono text-muted-foreground/60 ml-2">
            (포착률 기준, 셀 = 해당 조합 최고 score)
          </span>
        </div>
        {/* 헤더 */}
        <div className="flex gap-1">
          <div className="w-16 shrink-0" />
          {yVals.map(tr => (
            <div key={tr} className="w-16 text-center text-[10px] font-mono text-muted-foreground">
              trail {(tr*100).toFixed(0)}%
            </div>
          ))}
        </div>
        {/* 셀 */}
        {xVals.map(xv => (
          <div key={xv} className="flex gap-1 items-center">
            <div className="w-16 shrink-0 text-right text-[10px] font-mono text-muted-foreground pr-1">
              {isTP ? `TP ${(xv as number * 100).toFixed(0)}%` : `${xv}봉`}
            </div>
            {yVals.map(tr => {
              const k = `${xv}_${tr}`
              const row = cellMap.get(k)
              const cap = row ? metric(row) : 0
              const bw  = row?.big_winner_ratio ?? 0
              const bg  = row ? heatColor(cap, minS, maxS) : 'transparent'
              const isBest = row?.rank === 1
              return (
                <div
                  key={tr}
                  className={cn(
                    'w-16 h-12 flex flex-col items-center justify-center rounded text-[10px] font-mono',
                    isBest && 'ring-1 ring-yellow-400'
                  )}
                  style={{ backgroundColor: bg }}
                  title={row
                    ? `${isTP ? `TP=${(xv as number*100).toFixed(0)}%` : `hold=${xv}봉`} trail=${(tr*100).toFixed(0)}% → cap=${cap.toFixed(1)}% BW=${bw.toFixed(1)}% ret=${row.ret > 0 ? '+' : ''}${row.ret}%`
                    : ''}
                >
                  {row ? (
                    <>
                      <span className="text-white font-bold">{cap.toFixed(0)}%</span>
                      <span className="text-[8px]" style={{ color: bw >= 10 ? '#ffd700' : 'rgba(255,255,255,0.5)' }}>
                        BW {bw.toFixed(0)}%
                      </span>
                      {isBest && <span className="text-yellow-300 text-[7px]">BEST</span>}
                    </>
                  ) : (
                    <span className="text-muted-foreground">-</span>
                  )}
                </div>
              )
            })}
          </div>
        ))}
        <div className="text-[10px] text-muted-foreground mt-1 ml-16">
          ↑ {isTP ? 'TP(%)' : '보유봉'}
        </div>
        <div className="text-[10px] text-muted-foreground text-center">→ 트레일링(%)</div>
      </div>
    )
  }

  // ── TP/SL 히트맵 ─────────────────────────────────────────────────────────
  const tps    = [...new Set(rows.map(r => r.tp!))].sort((a, b) => a - b)
  const sls    = [...new Set(rows.map(r => r.sl!))].sort((a, b) => a - b)
  const map    = new Map(rows.map(r => [`${r.tp}_${r.sl}`, r]))
  const scores = rows.map(r => r.ret)
  const minS   = Math.min(...scores)
  const maxS   = Math.max(...scores)

  return (
    <div className="space-y-2">
      <div className="text-[11px] font-mono text-muted-foreground mb-1">
        히트맵 — 수익률 (TP × SL)
      </div>
      <div className="flex gap-1">
        <div className="w-10 shrink-0" />
        {tps.map(tp => (
          <div key={tp} className="w-14 text-center text-[10px] font-mono text-muted-foreground">
            {(tp * 100).toFixed(1)}%
          </div>
        ))}
      </div>
      {sls.map(sl => (
        <div key={sl} className="flex gap-1 items-center">
          <div className="w-10 shrink-0 text-right text-[10px] font-mono text-muted-foreground pr-1">
            {(sl * 100).toFixed(1)}%
          </div>
          {tps.map(tp => {
            const row = map.get(`${tp}_${sl}`)
            const ret = row?.ret ?? 0
            const bg  = row ? heatColor(ret, minS, maxS) : 'transparent'
            const isBest = row?.rank === 1
            return (
              <div
                key={tp}
                className={cn(
                  'w-14 h-10 flex flex-col items-center justify-center rounded text-[10px] font-mono',
                  isBest && 'ring-1 ring-yellow-400'
                )}
                style={{ backgroundColor: bg }}
                title={row ? `TP ${tp*100}% / SL ${sl*100}% → ret ${ret > 0 ? '+' : ''}${ret}%  win ${row.win_pct}%  RR ${row.rr}` : ''}
              >
                {row ? (
                  <>
                    <span className="text-white font-bold">{ret > 0 ? '+' : ''}{ret}%</span>
                    {isBest && <span className="text-yellow-300 text-[8px]">BEST</span>}
                  </>
                ) : (
                  <span className="text-muted-foreground">-</span>
                )}
              </div>
            )
          })}
        </div>
      ))}
      <div className="text-[10px] text-muted-foreground mt-1 ml-10">↑ SL (%)</div>
      <div className="text-[10px] text-muted-foreground text-center">→ TP (%)</div>
    </div>
  )
}

// ─── 결과 테이블 ──────────────────────────────────────────────────────────────

type SortKey = 'rank' | 'ret' | 'score' | 'win_pct' | 'rr' | 'mdd'
  | 'capture_rate' | 'avg_mfe_pct' | 'big_winner_ratio' | 'mfe_10plus_ratio'
  | 'avg_mae_pct' | 'mae_3plus_ratio' | 'sl_hit_ratio'
  | 'ret_d1' | 'ret_d2_5' | 'ret_d6_14' | 'ret_d15plus'

type TableSection = 'profit' | 'mae' | 'time'

function ResultsTable({ rows, mode, onApply, applyingKey, appliedKey }: {
  rows:        OptimizeRow[]
  mode:        Mode
  onApply?:    (row: OptimizeRow) => void
  applyingKey?: string | null
  appliedKey?:  string | null
}) {
  const [sortKey, setSortKey]         = useState<SortKey>('rank')
  const [asc, setAsc]                 = useState(true)
  const [sections, setSections]       = useState<Set<TableSection>>(new Set(['profit']))

  function toggleSection(s: TableSection) {
    setSections(prev => {
      const next = new Set(prev)
      if (next.has(s)) next.delete(s)
      else next.add(s)
      return next
    })
  }

  const rowKey = (r: OptimizeRow) =>
    mode === 'swing'
      ? `${r.min_hold}_${r.trailing}_${r.be_trigger}`
      : `${r.tp}_${r.sl}`

  const sorted = [...rows].sort((a, b) => {
    const va = (a as unknown as Record<string, number>)[sortKey] ?? 0
    const vb = (b as unknown as Record<string, number>)[sortKey] ?? 0
    const v = va < vb ? -1 : va > vb ? 1 : 0
    return asc ? v : -v
  })

  function toggleSort(key: SortKey) {
    if (sortKey === key) setAsc(p => !p)
    else { setSortKey(key); setAsc(key === 'rank') }
  }

  function Th({ k, label }: { k: SortKey; label: string }) {
    const active = sortKey === k
    return (
      <th
        className={cn(
          'px-2 py-1 text-right cursor-pointer select-none text-[11px] font-mono whitespace-nowrap',
          active ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'
        )}
        onClick={() => toggleSort(k)}
      >
        {label}{active ? (asc ? ' ↑' : ' ↓') : ''}
      </th>
    )
  }

  const showProfit = mode === 'swing' && sections.has('profit')
  const showMAE    = mode === 'swing' && sections.has('mae')
  const showTime   = mode === 'swing' && sections.has('time')

  function retColor(v: number) {
    return v > 0 ? 'text-success' : v < -0.5 ? 'text-destructive' : 'text-muted-foreground'
  }

  return (
    <div className="space-y-2">
      {/* 섹션 토글 (스윙 전용) */}
      {mode === 'swing' && (
        <div className="flex gap-1.5 items-center text-[10px] font-mono flex-wrap">
          <span className="text-muted-foreground">섹션:</span>
          {([
            ['profit', '수익구조'],
            ['mae',    'MAE 위험도'],
            ['time',   '시간대별 수익'],
          ] as [TableSection, string][]).map(([s, label]) => (
            <button
              key={s}
              onClick={() => toggleSection(s)}
              className={cn(
                'px-2 py-0.5 rounded border transition-colors',
                sections.has(s)
                  ? 'border-success text-success bg-success/10'
                  : 'border-border text-muted-foreground hover:border-foreground'
              )}
            >
              {label}
            </button>
          ))}
          <span className="text-muted-foreground/50 text-[9px] ml-1">
            MFE높음+MAE낮음=최고 | MFE높음+MAE높음=위험 | 둘다낮음=폐기
          </span>
        </div>
      )}
      <div className="overflow-auto">
        <table className="w-full text-[11px] font-mono">
          <thead>
            <tr className="border-b border-border">
              <Th k="rank" label="순위" />
              {mode === 'swing' ? (
                <>
                  <th className="px-2 py-1 text-left text-[11px] font-mono text-muted-foreground">TP</th>
                  <th className="px-2 py-1 text-left text-[11px] font-mono text-muted-foreground">보유</th>
                  <th className="px-2 py-1 text-left text-[11px] font-mono text-muted-foreground">트레일</th>
                  <th className="px-2 py-1 text-left text-[11px] font-mono text-muted-foreground">BE</th>
                </>
              ) : (
                <>
                  <th className="px-2 py-1 text-left text-[11px] font-mono text-muted-foreground">TP</th>
                  <th className="px-2 py-1 text-left text-[11px] font-mono text-muted-foreground">SL</th>
                </>
              )}
              <th className="px-2 py-1 text-right text-[11px] font-mono text-muted-foreground">거래</th>
              <Th k="win_pct" label="승률" />
              <Th k="rr"      label="R:R" />
              <Th k="mdd"     label="MDD" />
              <Th k="ret"     label="수익률" />
              {/* 수익구조 섹션 */}
              {showProfit && <>
                <Th k="capture_rate"     label="포착률" />
                <Th k="avg_mfe_pct"      label="MFE" />
                <Th k="big_winner_ratio" label="BW10%" />
                <Th k="mfe_10plus_ratio" label="잠재10%" />
              </>}
              {/* MAE 섹션 */}
              {showMAE && <>
                <Th k="avg_mae_pct"     label="MAE" />
                <Th k="mae_3plus_ratio" label="MAE3%+" />
                <Th k="sl_hit_ratio"    label="SL%" />
              </>}
              {/* 시간대 섹션 */}
              {showTime && <>
                <Th k="ret_d1"      label="1일" />
                <Th k="ret_d2_5"    label="2~5일" />
                <Th k="ret_d6_14"   label="6~14일" />
                <Th k="ret_d15plus" label="15일+" />
              </>}
              <Th k="score"   label="Score" />
              <th className="px-2 py-1 text-center text-[11px] font-mono text-muted-foreground">Pass</th>
              {onApply && <th className="px-2 py-1" />}
            </tr>
          </thead>
          <tbody>
            {sorted.map(r => {
              const key = rowKey(r)
              const isApplying = applyingKey === key
              const isApplied  = appliedKey  === key
              const mfe = r.avg_mfe_pct ?? 0
              const mae = r.avg_mae_pct ?? 0
              // MFE/MAE 진단: 색상으로 표현
              const mfeMaeOk = mfe >= 5 && mae < mfe * 0.6
              return (
                <tr
                  key={key}
                  className={cn(
                    'border-b border-border/30 hover:bg-muted/30',
                    r.rank === 1 && 'bg-yellow-950/20'
                  )}
                >
                  <td className="px-2 py-1 text-right">
                    {r.rank === 1 ? <span className="text-yellow-400">🥇</span> : r.rank}
                  </td>
                  {mode === 'swing' ? (
                    <>
                      <td className="px-2 py-1 text-foreground font-bold">{((r.tp ?? 0)*100).toFixed(0)}%</td>
                      <td className="px-2 py-1 text-accent font-bold">{r.min_hold}봉</td>
                      <td className="px-2 py-1 text-success font-bold">{((r.trailing ?? 0)*100).toFixed(0)}%</td>
                      <td className="px-2 py-1 text-muted-foreground">{((r.be_trigger ?? 0)*100).toFixed(0)}%</td>
                    </>
                  ) : (
                    <>
                      <td className="px-2 py-1 text-success font-bold">{((r.tp ?? 0)*100).toFixed(1)}%</td>
                      <td className="px-2 py-1 text-destructive font-bold">{((r.sl ?? 0)*100).toFixed(1)}%</td>
                    </>
                  )}
                  <td className="px-2 py-1 text-right text-muted-foreground">{r.trades}</td>
                  <td className={cn('px-2 py-1 text-right', r.win_pct >= 55 ? 'text-success' : 'text-muted-foreground')}>
                    {r.win_pct.toFixed(1)}%
                  </td>
                  <td className={cn('px-2 py-1 text-right', r.rr >= 1.5 ? 'text-success' : 'text-muted-foreground')}>
                    {r.rr.toFixed(2)}
                  </td>
                  <td className={cn('px-2 py-1 text-right', r.mdd >= -15 ? 'text-success' : 'text-destructive')}>
                    {r.mdd.toFixed(1)}%
                  </td>
                  <td className={cn('px-2 py-1 text-right font-bold', r.ret > 0 ? 'text-success' : 'text-destructive')}>
                    {r.ret > 0 ? '+' : ''}{r.ret.toFixed(1)}%
                  </td>
                  {/* 수익구조 */}
                  {showProfit && <>
                    <td className={cn('px-2 py-1 text-right', (r.capture_rate ?? 0) >= 40 ? 'text-success' : 'text-muted-foreground')}>
                      {(r.capture_rate ?? 0).toFixed(0)}%
                    </td>
                    <td className={cn('px-2 py-1 text-right', mfeMaeOk ? 'text-success' : 'text-muted-foreground')}
                        title={`MFE평균 ${mfe.toFixed(1)}% / MAE평균 ${mae.toFixed(1)}%`}>
                      {mfe.toFixed(1)}%
                    </td>
                    <td className={cn('px-2 py-1 text-right font-bold',
                          (r.big_winner_ratio ?? 0) >= 10 ? 'text-yellow-400' :
                          (r.big_winner_ratio ?? 0) >= 5  ? 'text-success' : 'text-muted-foreground')}
                        title="실현 수익 10%+ — 계좌 성장 핵심">
                      {(r.big_winner_ratio ?? 0).toFixed(1)}%
                    </td>
                    <td className={cn('px-2 py-1 text-right', (r.mfe_10plus_ratio ?? 0) >= 15 ? 'text-accent' : 'text-muted-foreground')}
                        title="MFE 10%+ 도달 비율 (전략 잠재력)">
                      {(r.mfe_10plus_ratio ?? 0).toFixed(1)}%
                    </td>
                  </>}
                  {/* MAE 위험도 */}
                  {showMAE && <>
                    <td className={cn('px-2 py-1 text-right',
                          mae <= 2 ? 'text-success' : mae <= 4 ? 'text-foreground' : 'text-destructive')}
                        title="평균 MAE — 낮을수록 안전한 진입">
                      {mae.toFixed(1)}%
                    </td>
                    <td className={cn('px-2 py-1 text-right',
                          (r.mae_3plus_ratio ?? 0) <= 20 ? 'text-success' :
                          (r.mae_3plus_ratio ?? 0) <= 40 ? 'text-foreground' : 'text-destructive')}
                        title="MAE>3% 거래 비율 — 높으면 위험하게 버팀">
                      {(r.mae_3plus_ratio ?? 0).toFixed(0)}%
                    </td>
                    <td className={cn('px-2 py-1 text-right',
                          (r.sl_hit_ratio ?? 0) <= 30 ? 'text-success' :
                          (r.sl_hit_ratio ?? 0) <= 50 ? 'text-foreground' : 'text-destructive')}
                        title="SL/BE_STOP 청산 비율">
                      {(r.sl_hit_ratio ?? 0).toFixed(0)}%
                    </td>
                  </>}
                  {/* 시간대별 수익 */}
                  {showTime && <>
                    <td className={cn('px-2 py-1 text-right text-[10px]', retColor(r.ret_d1 ?? 0))}
                        title={`1봉 보유 (${r.cnt_d1 ?? 0}건)`}>
                      {(r.ret_d1 ?? 0) > 0 ? '+' : ''}{(r.ret_d1 ?? 0).toFixed(1)}%
                    </td>
                    <td className={cn('px-2 py-1 text-right text-[10px]', retColor(r.ret_d2_5 ?? 0))}
                        title={`2~5봉 보유 (${r.cnt_d2_5 ?? 0}건)`}>
                      {(r.ret_d2_5 ?? 0) > 0 ? '+' : ''}{(r.ret_d2_5 ?? 0).toFixed(1)}%
                    </td>
                    <td className={cn('px-2 py-1 text-right text-[10px]', retColor(r.ret_d6_14 ?? 0))}
                        title={`6~14봉 보유 (${r.cnt_d6_14 ?? 0}건)`}>
                      {(r.ret_d6_14 ?? 0) > 0 ? '+' : ''}{(r.ret_d6_14 ?? 0).toFixed(1)}%
                    </td>
                    <td className={cn('px-2 py-1 text-right text-[10px] font-bold', retColor(r.ret_d15plus ?? 0))}
                        title={`15봉+ 보유 (${r.cnt_d15plus ?? 0}건) — 진짜 스윙`}>
                      {(r.ret_d15plus ?? 0) > 0 ? '+' : ''}{(r.ret_d15plus ?? 0).toFixed(1)}%
                    </td>
                  </>}
                  <td className="px-2 py-1 text-right text-accent">
                    {r.score.toFixed(mode === 'swing' ? 4 : 2)}
                  </td>
                  <td className="px-2 py-1 text-center text-muted-foreground">{r.passed}</td>
                  {onApply && (
                    <td className="px-2 py-1 text-center">
                      <button
                        onClick={() => onApply(r)}
                        disabled={isApplying}
                        className={cn(
                          "text-[10px] px-2 py-0.5 rounded border transition-colors",
                          isApplied  ? "border-success bg-success/10 text-success" :
                          isApplying ? "border-muted text-muted-foreground cursor-wait" :
                                       "border-border hover:border-success hover:text-success"
                        )}
                      >
                        {isApplying ? '적용중…' : isApplied ? '✓ 적용됨' : '적용'}
                      </button>
                    </td>
                  )}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ─── 멀티셀렉트 버튼 ──────────────────────────────────────────────────────────

function MultiSelect<T extends number>({
  label, options, selected, onToggle, fmt,
}: {
  label:    string
  options:  T[]
  selected: T[]
  onToggle: (v: T) => void
  fmt:      (v: T) => string
}) {
  return (
    <div className="space-y-1">
      <label className="text-[11px] font-mono text-muted-foreground">{label}</label>
      <div className="flex flex-wrap gap-1">
        {options.map(v => {
          const active = selected.includes(v)
          return (
            <button
              key={v}
              onClick={() => onToggle(v)}
              className={cn(
                'px-2 py-0.5 rounded text-[11px] font-mono border transition-colors',
                active
                  ? 'border-success text-success bg-success/10'
                  : 'border-border text-muted-foreground hover:border-foreground'
              )}
            >
              {fmt(v)}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// ─── 메인 뷰 ─────────────────────────────────────────────────────────────────

export function OptimizeView() {
  // ── form state ────────────────────────────────────────────────────────────
  const [mode, setMode]           = useState<Mode>('tp_sl')
  const [strategy, setStrategy]   = useState('B+VOL')
  const [start, setStart]         = useState('2022-01-01')
  const [end, setEnd]             = useState('2024-12-31')
  // tp_sl 모드
  const [tpPreset, setTpPreset]   = useState(1)
  const [slPreset, setSlPreset]   = useState(1)
  const [tpCustom, setTpCustom]   = useState('')
  const [slCustom, setSlCustom]   = useState('')
  // swing 모드
  const [tpSwingPreset, setTpSwingPreset] = useState(1)
  const [slSwingPreset, setSlSwingPreset] = useState(1)
  const [minHolds, setMinHolds]     = useState<number[]>([8, 24, 48])
  const [trailings, setTrailings]   = useState<number[]>([0.05, 0.08, 0.12])
  const [beTriggers, setBeTriggers] = useState<number[]>([0.03, 0.05])

  // ── job state ─────────────────────────────────────────────────────────────
  const [jobState, setJobState]   = useState<JobState>('idle')
  const [jobId, setJobId]         = useState<string | null>(null)
  const [status, setStatus]       = useState<OptimizeStatus | null>(null)
  const [results, setResults]     = useState<OptimizeResults | null>(null)
  const [view, setView]           = useState<'table' | 'heatmap'>('table')
  const [applyingKey, setApplyingKey] = useState<string | null>(null)
  const [appliedKey, setAppliedKey]   = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const tpValues = tpCustom.trim()
    ? tpCustom.trim().split(/[\s,]+/).map(v => parseFloat(v) / 100).filter(v => !isNaN(v))
    : TP_PRESETS[mode][tpPreset]?.values ?? TP_PRESETS[mode][0].values
  const slValues = slCustom.trim()
    ? slCustom.trim().split(/[\s,]+/).map(v => parseFloat(v) / 100).filter(v => !isNaN(v))
    : SL_PRESETS[mode][slPreset]?.values ?? SL_PRESETS[mode][0].values

  const totalCombos = mode === 'swing'
    ? minHolds.length * trailings.length * beTriggers.length
    : tpValues.length * slValues.length

  // mode 전환 시 preset index 초기화
  useEffect(() => {
    setTpPreset(1)
    setSlPreset(1)
    setTpCustom('')
    setSlCustom('')
  }, [mode])

  // ── polling ───────────────────────────────────────────────────────────────
  const stopPoll = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = null
  }, [])

  const fetchStatus = useCallback(async (id: string) => {
    try {
      const s = await getOptimizeStatus(id)
      setStatus(s)
      if (s.status === 'done') {
        stopPoll()
        setJobState('done')
        try {
          const r = await getOptimizeResults(id)
          setResults(r)
        } catch {
          setJobState('error')
          setStatus(prev => prev ? { ...prev, error: '결과 로드 실패' } : null)
        }
      } else if (s.status === 'error') {
        stopPoll()
        setJobState('error')
      }
    } catch {
      // status 폴링 실패 — 계속 재시도
    }
  }, [stopPoll])

  useEffect(() => {
    return () => stopPoll()
  }, [stopPoll])

  // ── handlers ──────────────────────────────────────────────────────────────
  async function handleRun() {
    const req: OptimizeRequest = {
      strategy,
      start,
      end,
      mode,
      tp_range: tpValues,
      sl_range: slValues,
      ...(mode === 'swing' && {
        min_hold_range:   minHolds,
        trailing_range:   trailings,
        be_trigger_range: beTriggers,
      }),
    }
    try {
      const { job_id } = await startOptimize(req)
      setJobId(job_id)
      setJobState('running')
      setStatus(null)
      setResults(null)
      pollRef.current = setInterval(() => fetchStatus(job_id), 1000)
    } catch {
      setJobState('error')
    }
  }

  async function handleCancel() {
    stopPoll()
    if (jobId) await cancelOptimize(jobId)
    setJobState('idle')
    setJobId(null)
    setStatus(null)
  }

  function handleReset() {
    stopPoll()
    setJobState('idle')
    setJobId(null)
    setStatus(null)
    setResults(null)
  }

  async function handleApply(row: OptimizeRow) {
    if (mode !== 'tp_sl') return
    const key = `${row.tp}_${row.sl}`
    setApplyingKey(key)
    try {
      await applyOptimize(row.tp!, row.sl!)
      setAppliedKey(key)
    } catch (e) {
      alert(`적용 실패: ${e}`)
    } finally {
      setApplyingKey(null)
    }
  }

  function toggleArr<T extends number>(arr: T[], v: T, set: (a: T[]) => void) {
    set(arr.includes(v) ? arr.filter(x => x !== v) : [...arr, v].sort((a, b) => a - b))
  }

  const progress  = status ? (status.progress / Math.max(status.total, 1)) * 100 : 0
  const isRunning = jobState === 'running'

  // 현재 결과의 mode (결과와 form mode가 다를 수 있음)
  const resultMode: Mode = results?.results[0]?.min_hold !== undefined ? 'swing' : 'tp_sl'

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* ── 좌측: 설정 패널 ──────────────────────────────────────────────── */}
      <aside className="w-72 shrink-0 border-r border-border bg-card overflow-y-auto">
        <div className="p-4 space-y-5">
          <div>
            <div className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider mb-3">
              전략 최적화
            </div>

            {/* 모드 스위처 */}
            <div className="space-y-1.5 mb-4">
              <label className="text-[11px] font-mono text-muted-foreground">최적화 모드</label>
              <div className="flex gap-1.5">
                {(['tp_sl', 'swing'] as const).map(m => (
                  <button
                    key={m}
                    onClick={() => setMode(m)}
                    className={cn(
                      'flex-1 px-2 py-1.5 rounded text-[11px] font-mono border transition-colors',
                      mode === m
                        ? 'border-accent text-accent bg-accent/10'
                        : 'border-border text-muted-foreground hover:border-foreground'
                    )}
                  >
                    {m === 'tp_sl' ? '단타 (TP/SL)' : '스윙 (트레일링)'}
                  </button>
                ))}
              </div>
            </div>

            {/* 전략 선택 */}
            <div className="space-y-1.5">
              <label className="text-[11px] font-mono text-muted-foreground">전략</label>
              <div className="flex flex-wrap gap-1.5">
                {STRATEGIES.map(s => (
                  <button
                    key={s}
                    onClick={() => setStrategy(s)}
                    className={cn(
                      'px-2 py-1 rounded text-[11px] font-mono border transition-colors',
                      strategy === s
                        ? 'border-success text-success bg-success/10'
                        : 'border-border text-muted-foreground hover:border-foreground'
                    )}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* 기간 */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-mono text-muted-foreground">기간</label>
            <div className="space-y-1">
              <input
                type="date" value={start} onChange={e => setStart(e.target.value)}
                className="w-full bg-background border border-border rounded px-2 py-1 text-[11px] font-mono text-foreground"
              />
              <input
                type="date" value={end} onChange={e => setEnd(e.target.value)}
                className="w-full bg-background border border-border rounded px-2 py-1 text-[11px] font-mono text-foreground"
              />
            </div>
          </div>

          {/* TP 범위 */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-mono text-muted-foreground">
              {mode === 'swing' ? '익절 상한(TP) 범위' : '익절(TP) 범위'}
            </label>
            <div className="flex flex-col gap-1">
              {TP_PRESETS[mode].map((p, i) => (
                <button
                  key={i}
                  onClick={() => { setTpPreset(i); setTpCustom('') }}
                  className={cn(
                    'text-left px-2 py-1 rounded text-[11px] font-mono border transition-colors',
                    tpPreset === i && !tpCustom
                      ? 'border-success text-success bg-success/10'
                      : 'border-border text-muted-foreground hover:border-foreground'
                  )}
                >
                  {p.label} — {p.values.map(v => `${v*100}%`).join(', ')}
                </button>
              ))}
              <input
                placeholder={mode === 'swing' ? '직접: 5 8 10 15 (%)' : '직접: 2 3 4 5 (%)'}
                value={tpCustom}
                onChange={e => setTpCustom(e.target.value)}
                className="bg-background border border-border rounded px-2 py-1 text-[11px] font-mono text-foreground placeholder:text-muted-foreground/50 mt-1"
              />
            </div>
            <div className="text-[10px] font-mono text-muted-foreground">
              선택됨: {tpValues.map(v => `${(v*100).toFixed(1)}%`).join(', ')}
            </div>
          </div>

          {/* SL 범위 */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-mono text-muted-foreground">손절(SL) 범위</label>
            <div className="flex flex-col gap-1">
              {SL_PRESETS[mode].map((p, i) => (
                <button
                  key={i}
                  onClick={() => { setSlPreset(i); setSlCustom('') }}
                  className={cn(
                    'text-left px-2 py-1 rounded text-[11px] font-mono border transition-colors',
                    slPreset === i && !slCustom
                      ? 'border-success text-success bg-success/10'
                      : 'border-border text-muted-foreground hover:border-foreground'
                  )}
                >
                  {p.label} — {p.values.map(v => `${v*100}%`).join(', ')}
                </button>
              ))}
              <input
                placeholder={mode === 'swing' ? '직접: 2 3 5 8 (%)' : '직접: 1 1.5 2 2.5 3 (%)'}
                value={slCustom}
                onChange={e => setSlCustom(e.target.value)}
                className="bg-background border border-border rounded px-2 py-1 text-[11px] font-mono text-foreground placeholder:text-muted-foreground/50 mt-1"
              />
            </div>
          </div>

          {/* 스윙 전용 파라미터 */}
          {mode === 'swing' && (
            <div className="space-y-3 border-t border-border pt-3">
              <div className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider">
                스윙 파라미터
              </div>
              <MultiSelect
                label="최소 보유봉"
                options={MIN_HOLD_OPTS}
                selected={minHolds}
                onToggle={v => toggleArr(minHolds, v, setMinHolds as (a: number[]) => void)}
                fmt={v => `${v}봉`}
              />
              <MultiSelect
                label="트레일링 스탑 (%)"
                options={TRAILING_OPTS}
                selected={trailings}
                onToggle={v => toggleArr(trailings, v, setTrailings as (a: number[]) => void)}
                fmt={v => `${(v*100).toFixed(0)}%`}
              />
              <MultiSelect
                label="BE 전환 트리거 (%)"
                options={BE_TRIGGER_OPTS}
                selected={beTriggers}
                onToggle={v => toggleArr(beTriggers, v, setBeTriggers as (a: number[]) => void)}
                fmt={v => `${(v*100).toFixed(0)}%`}
              />
              <div className="text-[10px] font-mono text-muted-foreground/70">
                * BE 트리거 &lt; 트레일링인 조합만 유효
              </div>
            </div>
          )}

          {/* 조합 수 요약 */}
          <div className="rounded border border-border bg-background p-2 text-[11px] font-mono space-y-0.5">
            <div className="flex justify-between text-muted-foreground">
              <span>전략</span><span className="text-foreground">{strategy}</span>
            </div>
            <div className="flex justify-between text-muted-foreground">
              <span>모드</span><span className="text-accent">{mode === 'tp_sl' ? '단타' : '스윙'}</span>
            </div>
            <div className="flex justify-between text-muted-foreground">
              <span>조합 수</span>
              <span><strong className="text-success font-bold">{totalCombos}</strong>개</span>
            </div>
          </div>

          {/* 실행 버튼 */}
          {!isRunning ? (
            <Button
              className="w-full gap-2 bg-success hover:bg-success/90 text-black"
              onClick={handleRun}
              disabled={totalCombos === 0}
            >
              <Play className="h-4 w-4" />
              Grid Search 실행
            </Button>
          ) : (
            <Button variant="destructive" className="w-full gap-2" onClick={handleCancel}>
              <Square className="h-4 w-4" />
              중단
            </Button>
          )}

          {(jobState === 'done' || jobState === 'error') && (
            <Button variant="outline" className="w-full gap-2" onClick={handleReset}>
              <RotateCcw className="h-4 w-4" />
              초기화
            </Button>
          )}
        </div>
      </aside>

      {/* ── 우측: 진행 + 결과 ────────────────────────────────────────────── */}
      <main className="flex flex-1 flex-col overflow-hidden">
        {/* 진행 상태 바 */}
        {(isRunning || jobState === 'done') && status && (
          <div className="shrink-0 border-b border-border bg-card px-4 py-2 space-y-1.5">
            <div className="flex items-center justify-between text-[11px] font-mono">
              <span className="text-muted-foreground">
                {isRunning ? `진행 중: ${status.progress} / ${status.total}` : `완료: ${status.total}조합`}
              </span>
              <span className="text-foreground">{status.message}</span>
              {jobState === 'done' && (
                <Badge className="bg-success/20 text-success border-success/30 font-mono text-[10px]">
                  완료
                </Badge>
              )}
            </div>
            <div className="h-1.5 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full rounded-full bg-success transition-all duration-300"
                style={{ width: `${jobState === 'done' ? 100 : progress}%` }}
              />
            </div>
          </div>
        )}

        {jobState === 'error' && (
          <div className="shrink-0 border-b border-destructive/30 bg-destructive/10 px-4 py-2 text-[11px] font-mono text-destructive">
            오류: {status?.error ?? '알 수 없는 오류'}
          </div>
        )}

        {jobState === 'done' && !results && jobId && (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 text-muted-foreground">
            <div className="text-[11px] font-mono animate-pulse">결과 로드 중...</div>
            <button
              className="text-[11px] font-mono border border-border rounded px-3 py-1 hover:border-foreground transition-colors"
              onClick={() => getOptimizeResults(jobId).then(setResults).catch(console.error)}
            >
              다시 불러오기
            </button>
          </div>
        )}

        {jobState === 'idle' && (
          <div className="flex flex-1 flex-col items-center justify-center gap-4 text-muted-foreground">
            <TrendingUp className="h-12 w-12 opacity-20" />
            <div className="text-center space-y-1">
              <div className="text-sm font-mono">전략 최적화 준비됨</div>
              <div className="text-[11px] font-mono opacity-60">
                좌측에서 모드·파라미터를 설정하고 Grid Search를 실행하세요
              </div>
            </div>
          </div>
        )}

        {isRunning && status && status.result_count > 0 && results === null && (
          <div className="flex flex-1 items-center justify-center">
            <div className="text-[11px] font-mono text-muted-foreground animate-pulse">
              {status.result_count}개 결과 수집 중...
            </div>
          </div>
        )}

        {/* 결과 표시 */}
        {results && results.results.length > 0 && (
          <div className="flex flex-1 flex-col overflow-hidden">
            {/* Best 하이라이트 */}
            {results.best && (
              <div className="shrink-0 border-b border-yellow-500/30 bg-yellow-950/20 px-4 py-2">
                <div className="flex items-center gap-3 text-[11px] font-mono">
                  <Trophy className="h-4 w-4 text-yellow-400" />
                  <span className="text-yellow-300 font-bold">최적 조합</span>
                  {resultMode === 'swing' ? (
                    <span className="text-muted-foreground">
                      hold=<span className="text-accent font-bold">{results.best.min_hold}봉</span>
                      {' '}trail=<span className="text-success font-bold">{((results.best.trailing ?? 0)*100).toFixed(0)}%</span>
                      {' '}BE=<span className="text-foreground">{((results.best.be_trigger ?? 0)*100).toFixed(0)}%</span>
                    </span>
                  ) : (
                    <span className="text-muted-foreground">
                      TP <span className="text-success font-bold">{((results.best.tp ?? 0)*100).toFixed(1)}%</span>
                      {' '}/ SL <span className="text-destructive font-bold">{((results.best.sl ?? 0)*100).toFixed(1)}%</span>
                    </span>
                  )}
                  <div className="ml-auto flex gap-3 text-muted-foreground">
                    <span>수익률 <strong className="text-success">{results.best.ret > 0 ? '+' : ''}{results.best.ret.toFixed(1)}%</strong></span>
                    {resultMode === 'swing' && <>
                      {results.best.capture_rate !== undefined && (
                        <span>포착률 <strong className={(results.best.capture_rate ?? 0) >= 40 ? 'text-success' : 'text-foreground'}>{(results.best.capture_rate ?? 0).toFixed(1)}%</strong></span>
                      )}
                      {results.best.big_winner_ratio !== undefined && (
                        <span title="실현 10%+ 거래 비율">BW <strong className={(results.best.big_winner_ratio ?? 0) >= 10 ? 'text-yellow-400' : 'text-foreground'}>{(results.best.big_winner_ratio ?? 0).toFixed(1)}%</strong></span>
                      )}
                      {results.best.mfe_10plus_ratio !== undefined && (
                        <span title="MFE 10%+ 도달 비율(잠재)">M10 <strong className="text-accent">{(results.best.mfe_10plus_ratio ?? 0).toFixed(1)}%</strong></span>
                      )}
                    </>}
                    <span>승률 <strong className={results.best.win_pct >= 55 ? 'text-success' : 'text-foreground'}>{results.best.win_pct.toFixed(1)}%</strong></span>
                    <span>MDD <strong className={results.best.mdd >= -15 ? 'text-success' : 'text-destructive'}>{results.best.mdd.toFixed(1)}%</strong></span>
                  </div>
                </div>
              </div>
            )}

            {/* 뷰 탭 */}
            <div className="shrink-0 flex border-b border-border px-4 gap-1 pt-1">
              {(['table', 'heatmap'] as const).map(v => (
                <button
                  key={v}
                  onClick={() => setView(v)}
                  className={cn(
                    'px-3 py-1 text-[11px] font-mono border-b-2 transition-colors',
                    view === v
                      ? 'border-success text-foreground'
                      : 'border-transparent text-muted-foreground hover:text-foreground'
                  )}
                >
                  {v === 'table' ? '결과 테이블' : '히트맵'}
                </button>
              ))}
            </div>

            {/* 테이블 / 히트맵 */}
            <div className="flex-1 overflow-auto p-4">
              {view === 'table' ? (
                <ResultsTable
                  rows={results.results}
                  mode={resultMode}
                  onApply={resultMode === 'tp_sl' ? handleApply : undefined}
                  applyingKey={applyingKey}
                  appliedKey={appliedKey}
                />
              ) : (
                <Heatmap rows={results.results} mode={resultMode} />
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
