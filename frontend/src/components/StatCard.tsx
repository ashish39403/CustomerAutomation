import type { ReactNode } from "react"
import { cn } from "../lib/cn"

type Tone = "ok" | "warn" | "info" | "neutral"

const TONES: Record<Tone, string> = {
  ok: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  warn: "bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  info: "bg-sky-50 text-sky-700 dark:bg-sky-950 dark:text-sky-300",
  neutral: "bg-soft text-muted-fg",
}

export interface StatCardProps {
  label: string
  value?: number
  icon: ReactNode
  tone?: Tone
  hint?: string
}

export function StatCard({ label, value, icon, tone = "neutral", hint }: StatCardProps) {
  return (
    <div className="rounded-lg border border-line bg-surface p-3">
      <div className="flex items-center gap-2">
        <span className={cn("grid size-7 place-items-center rounded-md", TONES[tone])}>{icon}</span>
        <span className="text-xs font-medium text-muted-fg">{label}</span>
      </div>
      {value === undefined ? (
        <div className="mt-2 h-7 w-14 animate-pulse rounded bg-soft" aria-hidden="true" />
      ) : (
        <p className="mt-1.5 text-2xl font-semibold tabular-nums">{value.toLocaleString()}</p>
      )}
      {hint && <p className="mt-1 text-[11px] text-muted-fg">{hint}</p>}
    </div>
  )
}
