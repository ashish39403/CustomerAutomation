import { StatusBadge } from "./status-badge"
import { UnavailableState } from "./states"
import { Button } from "@/components/ui/button"
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Skeleton } from "@/components/ui/skeleton"
import { Spinner } from "@/components/ui/spinner"
import { RefreshCw } from "lucide-react"
import { apiErrorMessage, isNotImplemented } from "@/lib/api"
import { formatDistanceToNowStrict } from "@/lib/time"
import type { JobListItem } from "@/lib/types"
import { cn } from "cn"

export interface JobTableProps {
  jobs: JobListItem[]
  loading: boolean
  error: unknown
  onRetryQuery: () => void
  onRetryJob?: (job: JobListItem) => void
  retryingJobId?: string | null
  className?: string
}

const GRID =
  "grid grid-cols-1 gap-1 sm:grid-cols-[minmax(0,1.6fr)_110px_90px_minmax(0,1.2fr)_120px] sm:items-center"

export function JobTable({
  jobs,
  loading,
  error,
  onRetryQuery,
  onRetryJob,
  retryingJobId = null,
  className,
}: JobTableProps) {
  if (error !== null && error !== undefined) {
    if (isNotImplemented(error)) {
      return <UnavailableState endpoint="GET /api/jobs" phase="jobs & queue" className={className} />
    }
    return (
      <div className="flex flex-col items-start gap-2 p-4">
        <p className="text-sm text-muted-foreground">{apiErrorMessage(error)}</p>
        <Button variant="outline" size="sm" onClick={onRetryQuery}>
          Retry
        </Button>
      </div>
    )
  }

  if (loading) {
    return (
      <div className={cn("flex flex-col gap-2 p-3", className)} aria-busy="true">
        <Spinner className="size-3.5 text-muted-foreground" />
        {Array.from({ length: 4 }, (_, index) => (
          <Skeleton key={index} className="h-9 w-full" />
        ))}
      </div>
    )
  }

  if (jobs.length === 0) {
    return (
      <Empty className={cn("py-10", className)}>
        <EmptyHeader>
          <EmptyTitle>No jobs yet</EmptyTitle>
          <EmptyDescription>
            Jobs appear when the Gmail poller or the worker starts processing.
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    )
  }

  return (
    <div className={cn("flex flex-col divide-y", className)}>
      {jobs.map((job) => (
        <div key={job.id} className={cn(GRID, "px-3 py-2")}>
          <span className="truncate text-sm font-medium">{job.job_type}</span>
          <span className="justify-self-start">
            <StatusBadge status={job.status} />
          </span>
          <span className="text-xs text-muted-foreground tabular-nums">
            {job.attempts}/{job.max_attempts}
          </span>
          <span className="truncate text-xs text-red-500" title={job.last_error ?? undefined}>
            {job.last_error ?? ""}
          </span>
          <div className="flex items-center justify-between gap-2 sm:justify-end">
            <span className="text-xs text-muted-foreground">
              {formatDistanceToNowStrict(job.updated_at)}
            </span>
            {job.status === "dead" && onRetryJob && (
              <Button
                variant="outline"
                size="sm"
                disabled={retryingJobId === job.id}
                onClick={() => onRetryJob(job)}
                title="Admin only — requeue this job"
              >
                {retryingJobId === job.id ? (
                  <>Retrying…</>
                ) : (
                  <>
                    <RefreshCw />
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
