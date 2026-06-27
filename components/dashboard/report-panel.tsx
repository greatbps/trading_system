'use client'

import { useState, useEffect, useCallback } from 'react'
import { X, ChevronLeft, ChevronRight, BarChart2, TrendingUp, Shield, Table2, Lightbulb, AlertTriangle, CheckCircle, Zap, Clock, Activity } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useTradingStore } from '@/store/trading'
import { cn } from '@/lib/utils'

// ─── Types ────────────────────────────────────────────────────────────────────

interface ReportSummary {
  total: number
  win_rate: number
  avg_pnl: number
  avg_net_pnl: number
  transaction_cost_pct: number
  tp1_count: number
  tp2_count: number
  be_count: number
  hs_count: number
}

interface SwingMetrics {
  avg_hold_h: number
  overnight_count: number
  hold_dist: { short: number; mid: number; long: number }
  short_win_rate: number | null
  mid_win_rate: number | null
  long_win_rate: number | null
  short_avg_pnl: number | null
  mid_avg_pnl: number | null
  long_avg_pnl: number | null
}

interface MfeMae {
  sample: number
  avg_mfe: number | null
  avg_mae: number | null
  entry_ok_count: number
  held_wrong_count: number
  no_demand_count: number
  avg_capture_rate: number | null
}

interface HealthBreakdown {
  label: string
  delta: number
}

interface HealthAction {
  param: string
  direction: string
  note: string
}

interface SafetyGate {
  can_apply: boolean
  blocked_by: string | null
  cooldown_remaining: number
  trades_since: number
  trades_required: number
  repeat_max: number
  repeat_limit: number
  kill_switch: boolean
  kill_switch_reasons: string[]
  recovery_eligible: boolean
  recovery_reason: string | null
  force_ok: boolean
  force_reason: string | null
  volume_ok: boolean
  volume_reason: string | null
}

interface Health {
  score: number
  level: string
  color: 'green' | 'amber' | 'red'
  breakdown: HealthBreakdown[]
  ops_verdict: string
  ops_type: 'healthy' | 'ops' | 'strategy' | 'stoploss' | 'daytrading' | 'mixed' | 'unknown'
  ops_detail: string
  confidence: 'LOW' | 'MID' | 'HIGH'
  confidence_note: string
  actions: HealthAction[]
  can_auto_apply: boolean
  auto_apply_enabled: boolean
  safety: SafetyGate
}

interface ParamChange {
  date: string
  timestamp: string
  ops_type: string
  ops_verdict: string
  health_score: number | null
  confidence: string | null
  changes: Array<{ param?: string; old?: unknown; new?: unknown; desc?: string; error?: string; action?: string }>
  backup: string
  applied: boolean
}

interface TrendEntry {
  date: string
  score: number
  level: string
  ops_type: string
  total: number
  wr: number
  avg_hold_h: number
}

interface HealthTrend {
  trend: TrendEntry[]
  avg_7d: number | null
  direction: 'up' | 'down' | 'flat' | 'unknown'
}

interface EarlyExit {
  structure_break: number
  ef_shakeout: number
  ef_no_demand: number
  ef_generic: number
  time_exit: number
  profit_exit: number
  ef_total: number
  ef_pct: number
}

interface Axis2Data {
  deferred: number
  fired: number
  hs_count: number
  hs_avg_loss: number
}

interface Axis3Data {
  buf_applied: number
  buf_skipped: number
  a_count: number
  a_win_rate: number
  a_avg_pnl: number
  a_stops: number
}

interface Axis4Row {
  grade: string
  exit_type: string
  count: number
  win_rate: number
  avg_pnl: number
}

interface Diagnosis {
  verdict: string
  positives: string[]
  warnings: string[]
  actions: string[]
}

interface DailyReport {
  date: string
  summary: ReportSummary
  health: Health
  swing: SwingMetrics
  mfemae: MfeMae
  early_exit: EarlyExit
  axis2: Axis2Data
  axis3: Axis3Data
  axis4: Axis4Row[]
  diagnosis: Diagnosis
  recommendations: string[]
  trades: unknown[]
}

// ─── Utils ────────────────────────────────────────────────────────────────────

function fmtDate(d: string) {
  return `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`
}

function pnlCls(v: number | null | undefined) {
  if (v == null) return 'text-muted-foreground'
  if (v > 0) return 'text-green-400'
  if (v < 0) return 'text-red-400'
  return 'text-muted-foreground'
}

function pct(v: number | null | undefined) {
  if (v == null || isNaN(v)) return '—'
  return `${v > 0 ? '+' : ''}${v.toFixed(1)}%`
}

function todayStr() {
  const d = new Date()
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`
}

function prevDay(d: string) {
  const dt = new Date(`${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`)
  dt.setDate(dt.getDate() - 1)
  return `${dt.getFullYear()}${String(dt.getMonth() + 1).padStart(2, '0')}${String(dt.getDate()).padStart(2, '0')}`
}

function nextDay(d: string) {
  const dt = new Date(`${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`)
  dt.setDate(dt.getDate() + 1)
  return `${dt.getFullYear()}${String(dt.getMonth() + 1).padStart(2, '0')}${String(dt.getDate()).padStart(2, '0')}`
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function SectionHeader({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-muted/30 border-b border-border sticky top-0 z-10">
      <span className="text-primary">{icon}</span>
      <span className="text-[11px] font-bold tracking-widest uppercase text-primary">{title}</span>
    </div>
  )
}

function KV({ label, value, cls }: { label: string; value: string | number; cls?: string }) {
  return (
    <div className="flex justify-between items-center py-1">
      <span className="text-[11px] text-muted-foreground">{label}</span>
      <span className={cn('text-[12px] font-mono font-bold', cls ?? 'text-foreground')}>{value}</span>
    </div>
  )
}

function Stat({ label, value, sub, cls }: { label: string; value: string | number; sub?: string; cls?: string }) {
  return (
    <div className="flex flex-col items-center gap-0.5 px-3 py-2 bg-muted/20 rounded border border-border">
      <span className="text-[10px] text-muted-foreground">{label}</span>
      <span className={cn('text-[16px] font-mono font-bold', cls ?? 'text-foreground')}>{value}</span>
      {sub && <span className="text-[10px] text-muted-foreground">{sub}</span>}
    </div>
  )
}

// ─── Summary ─────────────────────────────────────────────────────────────────

function SummarySection({ s }: { s: ReportSummary }) {
  return (
    <div className="p-4 space-y-3">
      <div className="grid grid-cols-4 gap-2">
        <Stat label="거래" value={s.total} />
        <Stat label="승률" value={`${s.win_rate}%`} cls={s.win_rate >= 50 ? 'text-green-400' : 'text-red-400'} />
        <Stat label="평균손익" value={pct(s.avg_pnl)} cls={pnlCls(s.avg_pnl)} />
        <Stat label="HS" value={s.hs_count} cls={s.hs_count > 0 ? 'text-red-400' : 'text-muted-foreground'} />
      </div>
      {s.avg_net_pnl !== undefined && (
        <div className="flex items-center justify-between px-2 py-1.5 bg-muted/10 rounded border border-border text-[11px]">
          <span className="text-muted-foreground">순손익 (수수료·세금 반영)</span>
          <span className={cn('font-mono font-bold', pnlCls(s.avg_net_pnl))}>
            {pct(s.avg_net_pnl)}
            <span className="text-[10px] text-muted-foreground ml-1">(-{s.transaction_cost_pct}%)</span>
          </span>
        </div>
      )}
      <div className="grid grid-cols-3 gap-2 text-[11px]">
        <div className="flex justify-between px-2 py-1 bg-muted/10 rounded border border-border">
          <span className="text-muted-foreground">TP1</span>
          <span className="font-mono text-green-400">{s.tp1_count}</span>
        </div>
        <div className="flex justify-between px-2 py-1 bg-muted/10 rounded border border-border">
          <span className="text-muted-foreground">TP2</span>
          <span className="font-mono text-green-400">{s.tp2_count}</span>
        </div>
        <div className="flex justify-between px-2 py-1 bg-muted/10 rounded border border-border">
          <span className="text-muted-foreground">BE</span>
          <span className="font-mono text-yellow-400">{s.be_count}</span>
        </div>
      </div>
    </div>
  )
}

// ─── Health Score ─────────────────────────────────────────────────────────────

const OPS_TYPE_META: Record<string, { label: string; bg: string; text: string }> = {
  healthy:    { label: '건강한 운영',    bg: 'bg-green-500/20 border-green-500/30', text: 'text-green-300'  },
  ops:        { label: '운영 실패',      bg: 'bg-amber-500/20 border-amber-500/30', text: 'text-amber-300'  },
  stoploss:   { label: '손절 위치 문제', bg: 'bg-amber-500/20 border-amber-500/30', text: 'text-amber-300'  },
  strategy:   { label: '전략 실패',      bg: 'bg-red-500/20 border-red-500/30',     text: 'text-red-300'    },
  daytrading: { label: '단타형 운영',    bg: 'bg-red-500/20 border-red-500/30',     text: 'text-red-300'    },
  mixed:      { label: '복합 문제',      bg: 'bg-muted/30 border-border',           text: 'text-muted-foreground' },
  unknown:    { label: '샘플 부족',      bg: 'bg-muted/30 border-border',           text: 'text-muted-foreground' },
}

const CONF_CLS: Record<string, string> = {
  LOW:  'text-red-400 bg-red-500/10 border-red-500/30',
  MID:  'text-amber-400 bg-amber-500/10 border-amber-500/30',
  HIGH: 'text-green-400 bg-green-500/10 border-green-500/30',
}

const TREND_ICON: Record<string, string> = { up: '↑', down: '↓', flat: '→', unknown: '—' }
const TREND_CLS:  Record<string, string>  = {
  up: 'text-green-400', down: 'text-red-400', flat: 'text-muted-foreground', unknown: 'text-muted-foreground',
}

function HealthScoreSection({ h, date, onApplied }: { h: Health; date: string; onApplied?: () => void }) {
  const [trend,       setTrend]       = useState<HealthTrend | null>(null)
  const [applying,    setApplying]    = useState(false)
  const [applyResult, setApplyResult] = useState<{ success: boolean; msg: string } | null>(null)

  useEffect(() => {
    globalThis.fetch('/trading/api/health-trend?days=7')
      .then(r => r.ok ? r.json() : null)
      .then(d => d && setTrend(d))
      .catch(() => {})
  }, [date])

  async function handleApply(force: boolean) {
    if (applying) return
    setApplying(true)
    setApplyResult(null)
    try {
      const res = await globalThis.fetch('/trading/api/auto-apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ops_type:     h.ops_type,
          health_score: h.score,
          confidence:   h.confidence,
          ops_verdict:  h.ops_verdict,
          force,
        }),
      })
      const data = await res.json()
      setApplyResult({ success: data.success, msg: data.error ?? `${data.applied?.length ?? 0}개 파라미터 적용됨` })
      if (data.success) onApplied?.()
    } catch {
      setApplyResult({ success: false, msg: '네트워크 오류' })
    } finally {
      setApplying(false)
    }
  }

  const barCls =
    h.color === 'green' ? 'bg-green-500' :
    h.color === 'amber' ? 'bg-amber-500' : 'bg-red-500'
  const levelCls =
    h.color === 'green' ? 'text-green-400' :
    h.color === 'amber' ? 'text-amber-400' : 'text-red-400'
  const ops = OPS_TYPE_META[h.ops_type] ?? OPS_TYPE_META.unknown

  return (
    <div className="p-4 space-y-3">
      {/* Score gauge + confidence */}
      <div className="flex items-center gap-3">
        <div className="flex flex-col items-center justify-center w-16 h-16 rounded-full border-2 border-border bg-muted/20 shrink-0">
          <span className={cn('text-[22px] font-mono font-bold leading-none', levelCls)}>{h.score}</span>
          <span className="text-[9px] text-muted-foreground">/100</span>
        </div>
        <div className="flex-1 space-y-1.5">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={cn('text-[15px] font-bold', levelCls)}>{h.level}</span>
            <span className={cn('text-[9px] font-mono px-1.5 py-0.5 rounded border', CONF_CLS[h.confidence])}>
              {h.confidence} · {h.confidence_note}
            </span>
          </div>
          <div className="h-2 rounded-full bg-muted/30 overflow-hidden">
            <div className={cn('h-full rounded-full', barCls)} style={{ width: `${h.score}%` }} />
          </div>
          <div className="flex justify-between text-[9px] text-muted-foreground">
            <span>0</span><span>50</span><span>80</span><span>100</span>
          </div>
        </div>
      </div>

      {/* Trend sparkline */}
      {trend && trend.trend.length > 1 && (
        <div className="flex items-center gap-2 px-3 py-1.5 rounded border border-border bg-muted/10">
          <span className="text-[10px] text-muted-foreground shrink-0">7일 추세</span>
          <div className="flex items-end gap-0.5 flex-1 h-6">
            {trend.trend.map((e, i) => {
              const h = Math.max(2, Math.round(e.score / 100 * 24))
              const cls = e.score >= 80 ? 'bg-green-500' : e.score >= 50 ? 'bg-amber-500' : 'bg-red-500'
              return (
                <div key={i} className="flex-1 flex flex-col justify-end" title={`${e.date}: ${e.score}점`}>
                  <div className={cn('w-full rounded-sm opacity-70', cls)} style={{ height: `${h}px` }} />
                </div>
              )
            })}
          </div>
          {trend.avg_7d != null && (
            <span className={cn('text-[11px] font-mono font-bold shrink-0', TREND_CLS[trend.direction])}>
              {TREND_ICON[trend.direction]} {trend.avg_7d}
            </span>
          )}
        </div>
      )}

      {/* Ops verdict */}
      <div className={cn('px-3 py-2 rounded border space-y-1', ops.bg)}>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-muted-foreground">운영 판정</span>
          <span className={cn('text-[12px] font-bold', ops.text)}>{h.ops_verdict}</span>
        </div>
        <p className="text-[11px] text-muted-foreground leading-relaxed">{h.ops_detail}</p>
      </div>

      {/* Safety Gates */}
      {h.safety && (
        <div className="space-y-1.5">
          {/* Kill Switch — 항상 표시, 최우선 */}
          {h.safety.kill_switch && (
            <div className="px-3 py-2 rounded border border-red-500/50 bg-red-500/15 space-y-1">
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] font-bold text-red-300">KILL SWITCH 활성</span>
                {h.safety.recovery_eligible
                  ? <span className="text-[9px] px-1 py-0.5 rounded bg-green-500/30 text-green-200">회복 게이트 통과</span>
                  : <span className="text-[9px] px-1 py-0.5 rounded bg-red-500/30 text-red-200">우회 불가</span>
                }
              </div>
              {h.safety.kill_switch_reasons.map((r, i) => (
                <div key={i} className="text-[11px] text-red-300">• {r}</div>
              ))}
              {h.safety.recovery_eligible && (
                <div className="text-[11px] text-green-300 border-t border-red-500/20 pt-1 mt-1">
                  ✓ 7일 평균 회복 확인 — 파라미터 조정 허용됨
                </div>
              )}
              {!h.safety.recovery_eligible && h.safety.recovery_reason && (
                <div className="text-[11px] text-red-300/70">
                  회복 조건 미충족: {h.safety.recovery_reason}
                </div>
              )}
            </div>
          )}

          {/* Volume Collapse 경고 */}
          {h.safety.volume_ok === false && (
            <div className="px-3 py-2 rounded border border-amber-500/40 bg-amber-500/10 space-y-1">
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] font-bold text-amber-300">거래량 붕괴 감지</span>
              </div>
              <div className="text-[11px] text-amber-300/80">{h.safety.volume_reason}</div>
            </div>
          )}

          {/* Gate status grid (kill switch 해제됐거나 비활성일 때) */}
          {(!h.safety.kill_switch || h.safety.recovery_eligible) && (
            <div className="grid grid-cols-3 gap-1.5">
              {/* Cooldown */}
              <div className={cn('flex flex-col px-2 py-1.5 rounded border text-center',
                h.safety.cooldown_remaining > 0
                  ? 'border-amber-500/30 bg-amber-500/10'
                  : 'border-green-500/20 bg-green-500/5'
              )}>
                <span className="text-[9px] text-muted-foreground">쿨다운</span>
                <span className={cn('text-[12px] font-bold font-mono',
                  h.safety.cooldown_remaining > 0 ? 'text-amber-400' : 'text-green-400'
                )}>
                  {h.safety.cooldown_remaining > 0 ? `${h.safety.cooldown_remaining}일` : '✓'}
                </span>
              </div>

              {/* Trades since change */}
              <div className={cn('flex flex-col px-2 py-1.5 rounded border text-center',
                h.safety.trades_since < h.safety.trades_required && h.safety.trades_since > 0
                  ? 'border-amber-500/30 bg-amber-500/10'
                  : 'border-green-500/20 bg-green-500/5'
              )}>
                <span className="text-[9px] text-muted-foreground">거래수</span>
                <span className={cn('text-[12px] font-bold font-mono',
                  h.safety.trades_since < h.safety.trades_required && h.safety.trades_since > 0
                    ? 'text-amber-400' : 'text-green-400'
                )}>
                  {h.safety.trades_since > 0
                    ? `${h.safety.trades_since}/${h.safety.trades_required}`
                    : '✓'}
                </span>
              </div>

              {/* Repeat count */}
              <div className={cn('flex flex-col px-2 py-1.5 rounded border text-center',
                h.safety.repeat_max >= h.safety.repeat_limit
                  ? 'border-red-500/30 bg-red-500/10'
                  : h.safety.repeat_max >= h.safety.repeat_limit - 1
                    ? 'border-amber-500/30 bg-amber-500/10'
                    : 'border-green-500/20 bg-green-500/5'
              )}>
                <span className="text-[9px] text-muted-foreground">반복</span>
                <span className={cn('text-[12px] font-bold font-mono',
                  h.safety.repeat_max >= h.safety.repeat_limit ? 'text-red-400' :
                  h.safety.repeat_max >= h.safety.repeat_limit - 1 ? 'text-amber-400' : 'text-green-400'
                )}>
                  {h.safety.repeat_max}/{h.safety.repeat_limit}
                </span>
              </div>
            </div>
          )}

          {/* Block reason */}
          {h.safety.blocked_by && !h.safety.kill_switch && (
            <div className="text-[11px] text-amber-300 px-2 py-1 rounded border border-amber-500/20 bg-amber-500/5">
              ⚠ {h.safety.blocked_by}
            </div>
          )}
        </div>
      )}

      {/* Action mapping */}
      {h.actions.length > 0 && (
        <div className="space-y-1.5 border border-blue-500/20 bg-blue-500/5 rounded p-3">
          <span className="text-[10px] font-bold text-blue-400">권장 파라미터 조정</span>
          {h.actions.map((a, i) => (
            <div key={i} className="flex items-start gap-2 text-[11px]">
              <span className={cn('font-mono shrink-0 font-bold',
                a.direction === '↑' || a.direction === 'ON' ? 'text-green-400' :
                a.direction === '↓' || a.direction === '←' ? 'text-red-400' : 'text-amber-400'
              )}>{a.direction}</span>
              <div className="flex-1 min-w-0">
                <span className="font-mono text-blue-300 text-[10px]">{a.param}</span>
                <span className="text-muted-foreground ml-1">— {a.note}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Auto Apply */}
      {h.actions.length > 0 && (!h.safety?.kill_switch || h.safety?.recovery_eligible) && (
        <div className="space-y-1.5 border-t border-border pt-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-muted-foreground font-bold">파라미터 적용</span>
            {!h.auto_apply_enabled && (
              <span className="text-[9px] text-muted-foreground px-1.5 py-0.5 rounded border border-border">
                auto_apply_enabled: false
              </span>
            )}
          </div>
          <div className="flex gap-2">
            {/* 게이트 통과한 경우 */}
            {h.can_auto_apply && h.auto_apply_enabled && (
              <Button size="sm" variant="default"
                className="flex-1 h-7 text-[11px] bg-blue-600 hover:bg-blue-500"
                disabled={applying}
                onClick={() => handleApply(false)}>
                {applying ? '적용 중…' : '자동 적용'}
              </Button>
            )}
            {/* force 적용 (force_ok 체크) */}
            <Button size="sm" variant="outline"
              className={cn('flex-1 h-7 text-[11px]',
                h.safety?.force_ok === false
                  ? 'border-red-500/30 text-red-400/50 cursor-not-allowed'
                  : h.safety?.can_apply
                    ? 'border-amber-500/50 text-amber-400 hover:bg-amber-500/10'
                    : 'border-border text-muted-foreground hover:bg-muted/20'
              )}
              disabled={applying || h.safety?.force_ok === false}
              title={h.safety?.force_ok === false ? (h.safety.force_reason ?? '') : ''}
              onClick={() => handleApply(true)}>
              {applying ? '적용 중…'
                : h.safety?.force_ok === false ? '강제 한도 초과'
                : h.safety?.can_apply ? '수동 적용 (force)'
                : '강제 적용 (게이트 우회)'}
            </Button>
          </div>
          {applyResult && (
            <div className={cn('text-[11px] px-2 py-1 rounded',
              applyResult.success ? 'bg-green-500/10 text-green-300' : 'bg-red-500/10 text-red-300'
            )}>
              {applyResult.success ? '✓ ' : '✗ '}{applyResult.msg}
            </div>
          )}
        </div>
      )}

      {/* Score breakdown */}
      {h.breakdown.length > 0 && (
        <div className="space-y-1 border-t border-border pt-2">
          <span className="text-[10px] text-muted-foreground font-bold">점수 구성</span>
          {h.breakdown.map((b, i) => (
            <div key={i} className="flex items-center justify-between text-[11px]">
              <span className="text-muted-foreground flex-1 truncate">{b.label}</span>
              <span className={cn('font-mono font-bold shrink-0 ml-2',
                b.delta > 0 ? 'text-green-400' : b.delta < 0 ? 'text-red-400' : 'text-muted-foreground'
              )}>
                {b.delta > 0 ? `+${b.delta}` : b.delta}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Swing Hold ───────────────────────────────────────────────────────────────

function SwingHoldSection({ d, total }: { d: SwingMetrics; total: number }) {
  const shortPct = total > 0 ? Math.round(d.hold_dist.short / total * 100) : 0
  const midPct   = total > 0 ? Math.round(d.hold_dist.mid   / total * 100) : 0
  const longPct  = total > 0 ? Math.round(d.hold_dist.long  / total * 100) : 0

  const holdCls = d.avg_hold_h < 1 ? 'text-red-400' : d.avg_hold_h < 4 ? 'text-amber-400' : 'text-green-400'

  return (
    <div className="p-4 space-y-3">
      {/* Header stats */}
      <div className="grid grid-cols-3 gap-2">
        <Stat label="평균 보유" value={`${d.avg_hold_h}h`} cls={holdCls} />
        <Stat label="오버나이트" value={d.overnight_count}
          cls={d.overnight_count > 0 ? 'text-blue-400' : 'text-muted-foreground'} />
        <Stat label="스윙 비율" value={`${longPct}%`}
          cls={longPct >= 30 ? 'text-green-400' : 'text-amber-400'}
          sub="(8h+)" />
      </div>

      {/* Hold distribution bar */}
      {total > 0 && (
        <div className="space-y-1.5">
          <span className="text-[10px] text-muted-foreground font-bold">보유 시간 분포</span>
          <div className="flex gap-0.5 h-5 rounded overflow-hidden">
            {d.hold_dist.short > 0 && (
              <div
                className="bg-red-500/60 flex items-center justify-center text-[9px] text-white font-mono"
                style={{ width: `${shortPct}%` }}
              >{d.hold_dist.short}</div>
            )}
            {d.hold_dist.mid > 0 && (
              <div
                className="bg-amber-500/60 flex items-center justify-center text-[9px] text-white font-mono"
                style={{ width: `${midPct}%` }}
              >{d.hold_dist.mid}</div>
            )}
            {d.hold_dist.long > 0 && (
              <div
                className="bg-blue-500/60 flex items-center justify-center text-[9px] text-white font-mono"
                style={{ width: `${longPct}%` }}
              >{d.hold_dist.long}</div>
            )}
          </div>
          <div className="flex gap-3 text-[10px] text-muted-foreground">
            <span><span className="inline-block w-2 h-2 bg-red-500/60 rounded-sm mr-1" />&lt;1h</span>
            <span><span className="inline-block w-2 h-2 bg-amber-500/60 rounded-sm mr-1" />1–8h</span>
            <span><span className="inline-block w-2 h-2 bg-blue-500/60 rounded-sm mr-1" />8h+</span>
          </div>
        </div>
      )}

      {/* Per-bucket win rate */}
      <div className="space-y-1 border-t border-border pt-2">
        <span className="text-[10px] text-muted-foreground font-bold">구간별 성과</span>
        {[
          { label: '단타형 (<1h)', wr: d.short_win_rate, avg: d.short_avg_pnl, n: d.hold_dist.short },
          { label: '반나절 (1–8h)', wr: d.mid_win_rate,   avg: d.mid_avg_pnl,   n: d.hold_dist.mid },
          { label: '스윙 (8h+)',   wr: d.long_win_rate,  avg: d.long_avg_pnl,  n: d.hold_dist.long },
        ].filter(r => r.n > 0).map((r, i) => (
          <div key={i} className="flex items-center justify-between text-[11px] py-0.5">
            <span className="text-muted-foreground w-28">{r.label}</span>
            <span className={cn('font-mono', r.wr != null && r.wr >= 50 ? 'text-green-400' : 'text-red-400')}>
              {r.wr != null ? `${r.wr}%` : '—'}
            </span>
            <span className={cn('font-mono', pnlCls(r.avg))}>{pct(r.avg)}</span>
            <span className="text-muted-foreground">{r.n}건</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── MFE/MAE Analysis ────────────────────────────────────────────────────────

function MfeMaeSection({ d }: { d: MfeMae }) {
  if (d.sample === 0) {
    return (
      <div className="p-4 text-[11px] text-muted-foreground text-center">
        MFE/MAE 데이터 없음 (신규 로그 형식 필요)
      </div>
    )
  }

  const captureCls =
    d.avg_capture_rate == null ? 'text-muted-foreground' :
    d.avg_capture_rate >= 60   ? 'text-green-400' :
    d.avg_capture_rate >= 40   ? 'text-amber-400' : 'text-red-400'

  const heldWrongPct = d.entry_ok_count > 0
    ? Math.round(d.held_wrong_count / d.entry_ok_count * 100) : 0

  return (
    <div className="p-4 space-y-3">
      {/* Top stats */}
      <div className="grid grid-cols-3 gap-2">
        <Stat label="평균 MFE" value={d.avg_mfe != null ? `${d.avg_mfe}%` : '—'}
          cls={d.avg_mfe != null && d.avg_mfe >= 1 ? 'text-green-400' : 'text-amber-400'} />
        <Stat label="평균 MAE" value={d.avg_mae != null ? `${d.avg_mae}%` : '—'}
          cls="text-red-400" />
        <Stat label="MFE 포착률" value={d.avg_capture_rate != null ? `${d.avg_capture_rate}%` : '—'}
          cls={captureCls} sub="방향 맞은 거래" />
      </div>

      {/* Entry diagnosis */}
      <div className="space-y-1.5 border-t border-border pt-2">
        <span className="text-[10px] text-muted-foreground font-bold">진입 진단</span>

        <div className="flex items-center justify-between text-[11px] py-0.5">
          <div>
            <span className="text-foreground">방향 맞음 (MFE ≥ 1%)</span>
            <span className="text-muted-foreground ml-1 text-[10px]">진입은 정확</span>
          </div>
          <span className="font-mono text-green-400">{d.entry_ok_count}건</span>
        </div>

        {d.held_wrong_count > 0 && (
          <div className="flex items-center justify-between text-[11px] py-0.5">
            <div>
              <span className="text-amber-300">방향 맞고 손절 ({heldWrongPct}%)</span>
              <span className="text-muted-foreground ml-1 text-[10px]">보유 실패</span>
            </div>
            <span className="font-mono text-amber-400">{d.held_wrong_count}건</span>
          </div>
        )}

        {d.no_demand_count > 0 && (
          <div className="flex items-center justify-between text-[11px] py-0.5">
            <div>
              <span className="text-red-300">방향 불발 (MFE &lt; 0.5%)</span>
              <span className="text-muted-foreground ml-1 text-[10px]">가짜 신호</span>
            </div>
            <span className="font-mono text-red-400">{d.no_demand_count}건</span>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Early Exit Classification ────────────────────────────────────────────────

function EarlyExitSection({ d, total }: { d: EarlyExit; total: number }) {
  const rows = [
    { label: '수익 청산',      sub: 'TP1/TP2/Trailing',     val: d.profit_exit,     cls: 'text-green-400',            note: '정상' },
    { label: '구조 붕괴',      sub: 'Hard Stop / Struct',    val: d.structure_break, cls: 'text-amber-400',            note: '전략적 정상' },
    { label: '흔들림 청산',    sub: 'EF no_follow — 버텨야', val: d.ef_shakeout,     cls: 'text-red-400',              note: '운영 문제' },
    { label: '가짜 신호',      sub: 'EF no_demand — 진입 문제', val: d.ef_no_demand, cls: 'text-red-400',              note: '신호 문제' },
    { label: '미분류 EF',      sub: 'Early Failure 기타',    val: d.ef_generic,      cls: 'text-muted-foreground',     note: '' },
    { label: '시간 청산',      sub: 'EOD / 시간 제한',        val: d.time_exit,       cls: 'text-blue-400',             note: '' },
  ].filter(r => r.val > 0)

  return (
    <div className="p-4 space-y-2">
      {/* EF summary */}
      <div className="flex items-center justify-between px-3 py-2 rounded border border-border bg-muted/10">
        <span className="text-[11px] text-muted-foreground">EF 비율</span>
        <span className={cn('text-[14px] font-mono font-bold', d.ef_pct >= 50 ? 'text-red-400' : d.ef_pct >= 30 ? 'text-amber-400' : 'text-foreground')}>
          {d.ef_pct}%
          <span className="text-[10px] font-normal text-muted-foreground ml-1">({d.ef_total}/{total}건)</span>
        </span>
      </div>

      {/* Breakdown */}
      <div className="space-y-1.5">
        {rows.map((r, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <span className={cn('text-[11px] font-mono', r.cls)}>{r.label}</span>
                {r.note && (
                  <span className={cn('text-[9px] px-1 py-0.5 rounded',
                    r.note === '정상' ? 'bg-green-500/20 text-green-400' :
                    r.note === '전략적 정상' ? 'bg-amber-500/20 text-amber-400' :
                    r.note === '운영 문제' ? 'bg-red-500/20 text-red-300' :
                    r.note === '신호 문제' ? 'bg-red-500/30 text-red-300' : ''
                  )}>{r.note}</span>
                )}
              </div>
              <div className="text-[10px] text-muted-foreground">{r.sub}</div>
            </div>
            <div className="text-right shrink-0">
              <span className={cn('text-[12px] font-mono font-bold', r.cls)}>{r.val}건</span>
              {total > 0 && (
                <span className="text-[10px] text-muted-foreground ml-1">
                  {Math.round(r.val / total * 100)}%
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Axis 2: Hard Stop ────────────────────────────────────────────────────────

function Axis2Section({ d }: { d: Axis2Data }) {
  return (
    <div className="p-4 space-y-2">
      <KV label="유예 횟수" value={d.deferred} />
      <KV label="실제 발동" value={d.fired} />
      <KV label="Hard Stop" value={d.hs_count} cls={d.hs_count > 0 ? 'text-red-400' : 'text-muted-foreground'} />
      <KV label="HS 평균손실" value={d.hs_count > 0 ? pct(d.hs_avg_loss) : '—'}
        cls={d.hs_avg_loss < 0 ? 'text-red-400' : 'text-muted-foreground'} />
    </div>
  )
}

// ─── Axis 3: A급 ─────────────────────────────────────────────────────────────

function Axis3Section({ d }: { d: Axis3Data }) {
  return (
    <div className="p-4 space-y-2">
      <KV label="버퍼 적용" value={d.buf_applied} />
      <KV label="버퍼 미적용" value={d.buf_skipped} />
      <div className="border-t border-border pt-2 mt-2 space-y-1">
        <KV label="A급 거래수" value={d.a_count} />
        <KV label="A급 승률" value={`${d.a_win_rate}%`} cls={d.a_win_rate >= 50 ? 'text-green-400' : 'text-red-400'} />
        <KV label="A급 평균손익" value={d.a_count > 0 ? pct(d.a_avg_pnl) : '—'} cls={pnlCls(d.a_avg_pnl)} />
        <KV label="A급 구조손절" value={d.a_stops} cls={d.a_stops > 0 ? 'text-red-400' : 'text-muted-foreground'} />
      </div>
    </div>
  )
}

// ─── Axis 4: 등급 × 청산유형 ─────────────────────────────────────────────────

function Axis4Section({ rows }: { rows: Axis4Row[] }) {
  if (rows.length === 0) {
    return <div className="p-4 text-[11px] text-muted-foreground text-center">데이터 없음</div>
  }
  return (
    <div className="p-4">
      <div className="grid grid-cols-5 text-[10px] text-muted-foreground pb-1 border-b border-border">
        <span>등급</span><span>청산유형</span><span className="text-right">건수</span>
        <span className="text-right">승률</span><span className="text-right">평균손익</span>
      </div>
      {rows.map((r, i) => (
        <div key={i} className="grid grid-cols-5 text-[11px] font-mono py-0.5 hover:bg-muted/20 rounded">
          <span className={r.grade === 'A' || r.grade === 'A+' ? 'text-green-400' : 'text-yellow-400'}>{r.grade}</span>
          <span className="text-muted-foreground truncate">{r.exit_type}</span>
          <span className="text-right text-foreground">{r.count}</span>
          <span className={cn('text-right', r.win_rate >= 50 ? 'text-green-400' : 'text-red-400')}>{r.win_rate}%</span>
          <span className={cn('text-right', pnlCls(r.avg_pnl))}>{pct(r.avg_pnl)}</span>
        </div>
      ))}
    </div>
  )
}

// ─── Diagnosis ───────────────────────────────────────────────────────────────

function DiagnosisSection({ d }: { d: Diagnosis }) {
  const verdictIsWarning =
    d.verdict.includes('단타형') || d.verdict.includes('스윙 전략 위반') || d.verdict.includes('샘플 부족')

  return (
    <div className="p-4 space-y-3">
      <div className={cn('px-3 py-2 rounded border',
        verdictIsWarning ? 'border-red-500/30 bg-red-500/10' : 'border-border bg-muted/20'
      )}>
        <span className="text-[10px] text-muted-foreground block mb-0.5">핵심 진단</span>
        <span className={cn('text-[13px] font-bold', verdictIsWarning ? 'text-red-300' : 'text-foreground')}>
          {d.verdict}
        </span>
      </div>

      {d.positives.length > 0 && (
        <div className="space-y-1.5">
          {d.positives.map((msg, i) => (
            <div key={i} className="flex gap-2 items-start">
              <CheckCircle className="h-3.5 w-3.5 text-green-400 shrink-0 mt-0.5" />
              <span className="text-[11px] text-green-300 leading-relaxed">{msg}</span>
            </div>
          ))}
        </div>
      )}

      {d.warnings.length > 0 && (
        <div className="space-y-1.5">
          {d.warnings.map((msg, i) => (
            <div key={i} className="flex gap-2 items-start">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-400 shrink-0 mt-0.5" />
              <span className="text-[11px] text-amber-200 leading-relaxed">{msg}</span>
            </div>
          ))}
        </div>
      )}

      {d.actions.length > 0 && (
        <div className="space-y-1.5 pt-1 border-t border-border">
          <span className="text-[10px] text-muted-foreground">액션</span>
          {d.actions.map((msg, i) => (
            <div key={i} className="flex gap-2 items-start">
              <Zap className="h-3.5 w-3.5 text-blue-400 shrink-0 mt-0.5" />
              <span className="text-[11px] text-blue-200 leading-relaxed">{msg}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Change History ───────────────────────────────────────────────────────────

function ChangeHistorySection({ onRolledBack }: { onRolledBack: () => void }) {
  const [changes,   setChanges]   = useState<ParamChange[]>([])
  const [rolling,   setRolling]   = useState(false)
  const [rollResult, setRollResult] = useState<string | null>(null)
  const [beforeAfter, setBeforeAfter] = useState<{
    has_data: boolean; verdict?: string; delta?: number | null
    before?: { avg_score: number | null; count: number }
    after?:  { avg_score: number | null; count: number }
    change_date?: string
  } | null>(null)

  useEffect(() => {
    globalThis.fetch('/trading/api/param-changes?limit=10')
      .then(r => r.ok ? r.json() : null)
      .then(d => d && setChanges(d.changes ?? []))
      .catch(() => {})
    globalThis.fetch('/trading/api/before-after')
      .then(r => r.ok ? r.json() : null)
      .then(d => d && setBeforeAfter(d))
      .catch(() => {})
  }, [])

  async function handleRollback() {
    if (rolling) return
    setRolling(true)
    setRollResult(null)
    try {
      const res  = await globalThis.fetch('/trading/api/rollback', { method: 'POST' })
      const data = await res.json()
      setRollResult(data.success ? '롤백 완료' : (data.error ?? '실패'))
      if (data.success) onRolledBack()
    } catch {
      setRollResult('네트워크 오류')
    } finally {
      setRolling(false)
    }
  }

  if (changes.length === 0 && !beforeAfter?.has_data) {
    return <div className="p-4 text-[11px] text-muted-foreground text-center">변경 이력 없음</div>
  }

  return (
    <div className="p-4 space-y-3">
      {/* Before / After comparison */}
      {beforeAfter?.has_data && (
        <div className="rounded border border-border bg-muted/10 p-3 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-muted-foreground font-bold">마지막 변경 효과</span>
            <span className={cn('text-[11px] font-bold',
              beforeAfter.verdict === '개선' ? 'text-green-400' :
              beforeAfter.verdict === '악화' ? 'text-red-400' : 'text-muted-foreground'
            )}>
              {beforeAfter.verdict === '개선' ? '↑ 개선' : beforeAfter.verdict === '악화' ? '↓ 악화' : '→ 유지'}
              {beforeAfter.delta != null && ` (${beforeAfter.delta > 0 ? '+' : ''}${beforeAfter.delta}점)`}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-[11px]">
            <div className="px-2 py-1.5 rounded bg-muted/20 border border-border">
              <div className="text-[10px] text-muted-foreground mb-0.5">변경 전 ({beforeAfter.before?.count ?? 0}일)</div>
              <div className="font-mono text-foreground">{beforeAfter.before?.avg_score ?? '—'}점</div>
            </div>
            <div className="px-2 py-1.5 rounded bg-muted/20 border border-border">
              <div className="text-[10px] text-muted-foreground mb-0.5">변경 후 ({beforeAfter.after?.count ?? 0}일)</div>
              <div className={cn('font-mono',
                (beforeAfter.after?.avg_score ?? 0) > (beforeAfter.before?.avg_score ?? 0) ? 'text-green-400' : 'text-red-400'
              )}>{beforeAfter.after?.avg_score ?? '—'}점</div>
            </div>
          </div>
          <div className="flex items-center justify-between text-[10px] text-muted-foreground">
            <span>변경일: {beforeAfter.change_date ?? '—'}</span>
            <button
              className={cn('text-[10px] px-2 py-0.5 rounded border',
                rolling ? 'border-border text-muted-foreground' : 'border-amber-500/40 text-amber-400 hover:bg-amber-500/10'
              )}
              onClick={handleRollback}
              disabled={rolling}
            >
              {rolling ? '롤백 중…' : '롤백'}
            </button>
          </div>
          {rollResult && (
            <div className="text-[11px] text-muted-foreground">{rollResult}</div>
          )}
        </div>
      )}

      {/* Change log */}
      {changes.length > 0 && (
        <div className="space-y-2">
          <span className="text-[10px] text-muted-foreground font-bold">변경 이력</span>
          {changes.slice(0, 6).map((c, i) => (
            <div key={i} className={cn('rounded border p-2 space-y-1',
              c.ops_type === 'ROLLBACK' ? 'border-border bg-muted/10' :
              c.applied ? 'border-blue-500/20 bg-blue-500/5' : 'border-red-500/20 bg-red-500/5'
            )}>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono text-muted-foreground">{c.date}</span>
                <span className={cn('text-[10px] font-bold',
                  c.ops_type === 'ROLLBACK' ? 'text-muted-foreground' :
                  c.applied ? 'text-blue-400' : 'text-red-400'
                )}>
                  {c.ops_type === 'ROLLBACK' ? 'ROLLBACK' : c.ops_verdict}
                  {c.health_score != null && ` (${c.health_score}점)`}
                </span>
              </div>
              {c.changes.slice(0, 3).map((ch, j) => (
                <div key={j} className="text-[10px] text-muted-foreground font-mono truncate">
                  {ch.action ? ch.action : ch.error
                    ? <span className="text-red-400">{ch.param}: {ch.error}</span>
                    : `${ch.param}: ${JSON.stringify(ch.old)} → ${JSON.stringify(ch.new)}`
                  }
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Recommendations ─────────────────────────────────────────────────────────

function RecommendationsSection({ items }: { items: string[] }) {
  if (items.length === 0) {
    return <div className="p-4 text-[11px] text-muted-foreground text-center">권고사항 없음</div>
  }
  return (
    <div className="p-4 space-y-2">
      {items.map((r, i) => (
        <div key={i} className="flex gap-2 text-[11px] leading-relaxed">
          <span className="text-primary shrink-0">▸</span>
          <span className="text-foreground">{r}</span>
        </div>
      ))}
    </div>
  )
}

// ─── Main Panel ───────────────────────────────────────────────────────────────

export function ReportPanel() {
  const { closePanel } = useTradingStore()
  const [date,    setDate]    = useState(todayStr)
  const [data,    setData]    = useState<DailyReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [histKey, setHistKey] = useState(0)  // force-refresh change history

  const loadReport = useCallback(async (d: string) => {
    setLoading(true)
    try {
      const res = await globalThis.fetch(`/trading/api/daily-report?date=${d}`)
      if (res.ok) setData(await res.json())
    } catch {
      // silently fail
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadReport(date) }, [date, loadReport])

  function refreshAll() { loadReport(date); setHistKey(k => k + 1) }

  const isToday = date === todayStr()

  return (
    <div className="flex flex-col h-full w-96 border-l border-border bg-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-muted/20 shrink-0">
        <div className="flex items-center gap-2">
          <BarChart2 className="h-4 w-4 text-primary" />
          <span className="text-[12px] font-bold tracking-wide">SWING REPORT</span>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" className="h-6 w-6"
            onClick={() => setDate(prevDay(date))}>
            <ChevronLeft className="h-3 w-3" />
          </Button>
          <span className="text-[11px] font-mono text-muted-foreground w-24 text-center">
            {fmtDate(date)}
          </span>
          <Button variant="ghost" size="icon" className="h-6 w-6"
            disabled={isToday}
            onClick={() => setDate(nextDay(date))}>
            <ChevronRight className="h-3 w-3" />
          </Button>
          <Button variant="ghost" size="icon" className="h-6 w-6 ml-1" onClick={closePanel}>
            <X className="h-3 w-3" />
          </Button>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex-1 flex items-center justify-center text-[11px] text-muted-foreground">
          로딩 중…
        </div>
      ) : !data || !data.summary?.total ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-2 text-muted-foreground">
          <BarChart2 className="h-8 w-8 opacity-20" />
          <span className="text-[11px]">거래 데이터 없음</span>
          <span className="text-[10px] opacity-50">{fmtDate(date)}</span>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto">
          {/* Summary */}
          <SectionHeader icon={<TrendingUp className="h-3.5 w-3.5" />} title="요약" />
          <SummarySection s={data.summary} />

          {/* Health Score */}
          {data.health && (
            <>
              <SectionHeader icon={<Activity className="h-3.5 w-3.5" />} title="전략 건강도" />
              <HealthScoreSection h={data.health} date={date} onApplied={refreshAll} />
            </>
          )}

          {/* Swing Hold */}
          {data.swing && (
            <>
              <SectionHeader icon={<Clock className="h-3.5 w-3.5" />} title="보유 지속성" />
              <SwingHoldSection d={data.swing} total={data.summary.total} />
            </>
          )}

          {/* MFE/MAE */}
          {data.mfemae && (
            <>
              <SectionHeader icon={<Activity className="h-3.5 w-3.5" />} title="MFE / MAE 분석" />
              <MfeMaeSection d={data.mfemae} />
            </>
          )}

          {/* Early Exit */}
          {data.early_exit && (
            <>
              <SectionHeader icon={<Zap className="h-3.5 w-3.5" />} title="조기 청산 분류" />
              <EarlyExitSection d={data.early_exit} total={data.summary.total} />
            </>
          )}

          {/* Diagnosis */}
          {data.diagnosis && (
            <>
              <SectionHeader icon={<AlertTriangle className="h-3.5 w-3.5" />} title="진단" />
              <DiagnosisSection d={data.diagnosis} />
            </>
          )}

          {/* Axis 2 */}
          <SectionHeader icon={<Shield className="h-3.5 w-3.5" />} title="Hard Stop 검증" />
          <Axis2Section d={data.axis2} />

          {/* Axis 3 */}
          <SectionHeader icon={<Shield className="h-3.5 w-3.5" />} title="A급 노이즈 버퍼" />
          <Axis3Section d={data.axis3} />

          {/* Axis 4 */}
          <SectionHeader icon={<Table2 className="h-3.5 w-3.5" />} title="등급 × 청산유형" />
          <Axis4Section rows={data.axis4} />

          {/* Change History */}
          <SectionHeader icon={<Shield className="h-3.5 w-3.5" />} title="파라미터 변경 이력" />
          <ChangeHistorySection key={histKey} onRolledBack={refreshAll} />

          {/* Recommendations */}
          <SectionHeader icon={<Lightbulb className="h-3.5 w-3.5" />} title="권고사항" />
          <RecommendationsSection items={data.recommendations} />
        </div>
      )}
    </div>
  )
}
