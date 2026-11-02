import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Spinner } from "@/components/ui/spinner"
import { cn } from "cn"

export function ErrorState({
  message,
  onRetry,
  className,
}: {
  message: string
  onRetry?: () => void
  className?: string
}) {
  return (
    <div className={cn("flex flex-col items-start gap-3 p-4", className)}>
      <Alert variant="destructive">
        <AlertTitle>Something went wrong</AlertTitle>
        <AlertDescription>{message}</AlertDescription>
      </Alert>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  )
}

export function LoadingState({
  label,
  rows = 4,
  className,
}: {
  label?: string
  rows?: number
  className?: string
}) {
  return (
    <div className={cn("flex flex-col gap-2 p-4", className)} aria-busy="true">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Spinner className="size-3.5" />
        {label ?? "Loading…"}
      </div>
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton key={index} className="h-10 w-full" />
      ))}
    </div>
  )
}

/** Rendered when an agreed endpoint does not exist on the backend yet. */
export function UnavailableState({
  endpoint,
  phase,
  className,
}: {
  endpoint: string
  phase: string
  className?: string
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-1.5 px-4 py-10 text-center",
        className,
      )}
    >
      <p className="text-sm font-medium">Not available yet</p>
      <p className="max-w-sm text-xs text-muted-foreground">
        The backend does not serve <span className="font-mono">{endpoint}</span> yet. It comes online
        with the {phase} phase — the UI is already wired for it.
      </p>
    </div>
  )
}
