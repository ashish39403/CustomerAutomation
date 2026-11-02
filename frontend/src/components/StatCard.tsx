import type { ReactNode } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "cn"

type Tone = "ok" | "warn" | "info" | "neutral"

const TONES: Record<Tone, string> = {
  ok: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  warn: "bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  info: "bg-sky-50 text-sky-700 dark:bg-sky-950 dark:text-sky-300",
  neutral: "bg-secondary text-secondary-foreground",
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
    <Card className="gap-0 py-3">
      <CardContent className="flex flex-col gap-2 px-3">
        <div className="flex items-center gap-2">
          <span className={cn("grid size-7 place-items-center rounded-md", TONES[tone])}>{icon}</span>
          <span className="text-xs font-medium text-muted-foreground">{label}</span>
        </div>
        {value === undefined ? (
          <Skeleton className="mt-1 h-7 w-14" />
        ) : (
          <p className="mt-1.5 text-2xl font-semibold tabular-nums">{value.toLocaleString()}</p>
        )}
        {hint && <p className="text-[11px] text-muted-foreground">{hint}</p>}
      </CardContent>
    </Card>
  )
}
