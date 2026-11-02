import { formatDistanceToNowStrict } from "../lib/time"
import { StatusBadge } from "./ui/StatusBadge"
import { EmptyState, ErrorState, LoadingState } from "./ui/States"
import { Button } from "./ui/Button"
import { RefreshIcon } from "./ui/icons"
import { apiErrorMessage } from "../lib/api"
import type { JobListItem } from "../lib/types"
import { cn } from "../lib/cn"

export interface JobTableProps {
  jobs: JobListItem[]
  loading: boolean
  error: unknown
  onRetry: () => void
  onRetryJob?: (job: JobListItem) => void
  retryingJobId?: string | null
  emptyTitle?: string
  className?: string
}

const GRID =
  "grid grid-cols-1 gap-1 sm:grid-cols-[minmax(0,1.6fr)_110px_90px_minmax(0,1.4fr)_120px] sm:items-center"

export function JobTable({
  jobs,
  loading,
  error,
  onRetry,
  onRetryJob,
  retryingJobId = null,
  emptyTitle = "No jobs yet",
  className,
}: JobTableProps) {
  if (error !== null && error !== undefined) {
    return <ErrorState message={apiErrorMessage(error)} onRetry={onRetry} className={className} />
  }

  if (loading) {
    return <LoadingState label="Loading jobs…" className={className} />
  }

  if (jobs.length === 0) {
    return (
      <EmptyState
        title={emptyTitle}
        hint="Jobs appear when the Gmail poller or worker runs."
        className={className}
      />
    )
  }

  return (
    <div className={cn("flex flex-col divide-y divide-line", className)}>
      {jobs.map((job) => (
        <div key={job.id} className={cn(GRID, "px-3 py-2")}>
          <span className="truncate text-sm font-medium" title={job.last_error ?? undefined}>
            {job.job_type}
          </span>
          <span className="justify-self-start">
            <StatusBadge status={job.status} />
          </span>
          <span className="text-xs text-muted-fg tabular-nums">
            {job.attempts}/{job.max_attempts}
          </span>
          <span className="truncate text-xs text-red-500" title={job.last_error ?? undefined}>
            {job.last_error ?? ""}
          </span>
          <div className="flex items-center justify-between gap-2 sm:justify-end">
            <span className="text-xs text-muted-fg">{formatDistanceToNowStrict(job.updated_at)}</span>
            {job.status === "dead" && onRetryJob && (
              <Button
                variant="outline"
                size="sm"
                disabled={retryingJobId === job.id}
                onClick={() => onRetryJob(job)}
                title="Admin only — requeue this job"
              >
                {retryingJobId === job.id ? (
                  "Retrying…"
                ) : (
                  <>
                    <RefreshIcon />
                    Retry
                  </>
                )}
              </Button>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
