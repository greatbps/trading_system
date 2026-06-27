'use client'

import { X, AlertTriangle, Info, AlertCircle, CheckCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useTradingStore } from '@/store/trading'
import { cn } from '@/lib/utils'

const LEVEL_CONFIG = {
  error:   { icon: AlertCircle,   cls: 'text-red-400',    bg: 'bg-red-400/5'    },
  warning: { icon: AlertTriangle, cls: 'text-amber-400',  bg: 'bg-amber-400/5'  },
  info:    { icon: Info,          cls: 'text-blue-400',   bg: ''                },
  debug:   { icon: CheckCircle,   cls: 'text-muted-foreground', bg: ''          },
} as const

export function ErrorsPanel() {
  const { debugLogs, closePanel } = useTradingStore()

  const errors   = debugLogs.filter(l => l.level === 'error')
  const warnings = debugLogs.filter(l => l.level === 'warning')

  return (
    <div className="flex flex-col h-full w-80 border-l border-border bg-card overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-muted/20 shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-[12px] font-bold tracking-wide">알림 · 로그</span>
          {errors.length > 0 && (
            <span className="px-1.5 py-0.5 rounded bg-red-400/20 text-red-400 text-[10px] font-mono">{errors.length}에러</span>
          )}
          {warnings.length > 0 && (
            <span className="px-1.5 py-0.5 rounded bg-amber-400/20 text-amber-400 text-[10px] font-mono">{warnings.length}경고</span>
          )}
        </div>
        <Button variant="ghost" size="icon" className="h-6 w-6" onClick={closePanel}>
          <X className="h-3 w-3" />
        </Button>
      </div>

      {debugLogs.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-2 text-muted-foreground">
          <CheckCircle className="h-8 w-8 opacity-20" />
          <span className="text-[11px]">알림 없음</span>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto">
          {debugLogs.map((log) => {
            const cfg = LEVEL_CONFIG[log.level] ?? LEVEL_CONFIG.info
            const Icon = cfg.icon
            return (
              <div key={log.id} className={cn(
                'flex gap-2 px-3 py-2 border-b border-border/50',
                cfg.bg
              )}>
                <Icon className={cn('h-3.5 w-3.5 shrink-0 mt-0.5', cfg.cls)} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2 mb-0.5">
                    <span className={cn('text-[10px] font-mono font-bold', cfg.cls)}>{log.module}</span>
                    <span className="text-[10px] text-muted-foreground font-mono">{log.time}</span>
                  </div>
                  <span className="text-[11px] text-foreground leading-relaxed break-words">{log.msg}</span>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
