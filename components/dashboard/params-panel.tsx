'use client'

import { useState } from 'react'
import { X, RotateCcw, Save } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useTradingStore } from '@/store/trading'
import { cn } from '@/lib/utils'
import type { Param } from '@/src/types/trading'

function ParamRow({ param, onUpdate }: { param: Param; onUpdate: (key: string, value: Param['value']) => void }) {
  const [local, setLocal] = useState(String(param.value))

  const commit = () => {
    if (param.type === 'number') {
      const n = parseFloat(local)
      if (!isNaN(n)) onUpdate(param.key, n)
    } else {
      onUpdate(param.key, local)
    }
  }

  return (
    <div className={cn(
      'flex items-center justify-between px-3 py-2 gap-3 border-b border-border/50',
      param.dirty && 'bg-amber-400/5'
    )}>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] font-mono text-foreground truncate">{param.label}</span>
          {param.dirty && <span className="text-[9px] text-amber-400 font-bold">수정됨</span>}
        </div>
        <span className="text-[10px] text-muted-foreground leading-tight">{param.description}</span>
      </div>

      <div className="shrink-0">
        {param.type === 'boolean' ? (
          <button
            onClick={() => onUpdate(param.key, !param.value)}
            className={cn(
              'px-2 py-0.5 rounded text-[11px] font-mono border transition-colors',
              param.value ? 'border-green-500/50 text-green-400 bg-green-400/10' : 'border-border text-muted-foreground'
            )}
          >
            {param.value ? 'ON' : 'OFF'}
          </button>
        ) : param.type === 'select' && param.options ? (
          <select
            value={String(param.value)}
            onChange={e => onUpdate(param.key, e.target.value)}
            className="bg-background border border-border rounded px-2 py-0.5 text-[11px] font-mono text-foreground"
          >
            {param.options.map(o => <option key={o} value={o}>{o}</option>)}
          </select>
        ) : (
          <input
            type="number"
            value={local}
            min={param.min}
            max={param.max}
            step={param.step ?? 1}
            onChange={e => setLocal(e.target.value)}
            onBlur={commit}
            onKeyDown={e => e.key === 'Enter' && commit()}
            className="w-20 bg-background border border-border rounded px-2 py-0.5 text-[11px] font-mono text-foreground text-right"
          />
        )}
      </div>
    </div>
  )
}

export function ParamsPanel() {
  const { params, updateParam, closePanel } = useTradingStore()

  const dirty = params.filter(p => p.dirty)
  const groups = params.reduce<Record<string, Param[]>>((acc, p) => {
    const g = p.key.split('.')[0] ?? 'general'
    ;(acc[g] ??= []).push(p)
    return acc
  }, {})

  return (
    <div className="flex flex-col h-full w-80 border-l border-border bg-card overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-muted/20 shrink-0">
        <span className="text-[12px] font-bold tracking-wide">전략 파라미터</span>
        <div className="flex items-center gap-1">
          {dirty.length > 0 && (
            <span className="text-[10px] text-amber-400 font-mono">{dirty.length}개 수정됨</span>
          )}
          <Button variant="ghost" size="icon" className="h-6 w-6" onClick={closePanel}>
            <X className="h-3 w-3" />
          </Button>
        </div>
      </div>

      {params.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-2 text-muted-foreground">
          <Save className="h-8 w-8 opacity-20" />
          <span className="text-[11px]">파라미터 데이터 없음</span>
          <span className="text-[10px] opacity-50">API 서버 연결 확인</span>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto">
          {Object.entries(groups).map(([group, items]) => (
            <div key={group}>
              <div className="px-3 py-1.5 bg-muted/30 border-b border-border sticky top-0">
                <span className="text-[10px] font-bold tracking-widest uppercase text-muted-foreground">{group}</span>
              </div>
              {items.map(p => (
                <ParamRow key={p.key} param={p} onUpdate={updateParam} />
              ))}
            </div>
          ))}
        </div>
      )}

      {dirty.length > 0 && (
        <div className="flex gap-2 px-3 py-2 border-t border-border bg-muted/10 shrink-0">
          <Button
            variant="ghost"
            size="sm"
            className="flex-1 h-7 text-[11px] gap-1.5"
            onClick={() => dirty.forEach(p => updateParam(p.key, p.defaultValue))}
          >
            <RotateCcw className="h-3 w-3" />
            초기화
          </Button>
          <Button
            size="sm"
            className="flex-1 h-7 text-[11px] gap-1.5 bg-success hover:bg-success/90 text-black"
          >
            <Save className="h-3 w-3" />
            저장
          </Button>
        </div>
      )}
    </div>
  )
}
