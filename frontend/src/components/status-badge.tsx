import { Badge } from "@/components/ui/badge"
import { cn } from "cn"

// Domain status colors: no single token fits every state, so the palette
// classes are explicit here and dark: variants keep contrast in both themes.
const LABELS: Record<string, string> = {
  auto_replied: "Auto-replied",
  handed_off: "Handed off",
  pending: "Pending",
  queued: "Queued",
  running: "Running",
  succeeded: "Succeeded",
  retry_wait: "Retrying",
  dead: "Dead",
}

const STYLES: Record<string, string> = {
  auto_replied:
    "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-300",
  handed_off:
    "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-300",
  pending:
    "border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-900 dark:bg-sky-950 dark:text-sky-300",
  queued:
    "border-violet-200 bg-violet-50 text-violet-700 dark:border-violet-900 dark:bg-violet-950 dark:text-violet-300",
  running:
    "border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-900 dark:bg-sky-950 dark:text-sky-300",
  succeeded:
    "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-300",
  retry_wait:
    "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-300",
  dead:
    "border-red-200 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300",
}

export function StatusBadge({ status, className }: { status: string; className?: string }) {
  return (
    <Badge variant="outline" className={cn("rounded-full font-medium", STYLES[status], className)}>
      {LABELS[status] ?? status}
    </Badge>
  )
}
