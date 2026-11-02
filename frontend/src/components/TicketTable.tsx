import { StatusBadge } from "./status-badge"
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Skeleton } from "@/components/ui/skeleton"
import { formatDate } from "@/lib/format"
import type { Ticket } from "@/lib/types"
import { apiErrorMessage, isNotImplemented } from "@/lib/api"
import { UnavailableState } from "./states"
import { cn } from "cn"

export interface TicketTableProps {
  tickets: Ticket[]
  loading: boolean
  error: unknown
  onRetry: () => void
  onOpen: (ticket: Ticket) => void
  emptyTitle?: string
  emptyHint?: string
  className?: string
}

const GRID =
  "grid grid-cols-1 gap-1 sm:grid-cols-[minmax(0,2fr)_minmax(0,1.6fr)_120px_130px] sm:items-center"

export function TicketTable({
  tickets,
  loading,
  error,
  onRetry,
  onOpen,
  emptyTitle = "No tickets",
  emptyHint,
  className,
}: TicketTableProps) {
  if (error !== null && error !== undefined) {
    if (isNotImplemented(error)) {
      return <UnavailableState endpoint="GET /api/tickets" phase="ticket pipeline" className={className} />
    }
    return (
      <div className="p-4">
        <p className="text-sm text-muted-foreground">{apiErrorMessage(error)}</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 text-xs font-medium text-primary underline-offset-4 hover:underline"
        >
          Retry
        </button>
      </div>
    )
  }

  if (loading) {
    return (
      <div className={cn("flex flex-col gap-2 p-3", className)} aria-busy="true">
        {Array.from({ length: 5 }, (_, index) => (
          <div key={index} className={cn(GRID)}>
            <Skeleton className="h-4 w-3/5" />
            <Skeleton className="h-3.5 w-2/5" />
            <Skeleton className="h-4 w-20 rounded-full" />
            <Skeleton className="h-3.5 w-24" />
          </div>
        ))}
      </div>
    )
  }

  if (tickets.length === 0) {
    return (
      <Empty className={cn("py-12", className)}>
        <EmptyHeader>
          <EmptyTitle>{emptyTitle}</EmptyTitle>
          {emptyHint && <EmptyDescription>{emptyHint}</EmptyDescription>}
        </EmptyHeader>
      </Empty>
    )
  }

  return (
    <div className={cn("flex flex-col divide-y", className)}>
      <div
        className={cn(
          GRID,
          "hidden px-3 pb-2 pt-3 text-[11px] font-medium uppercase tracking-wide text-muted-foreground sm:grid",
        )}
      >
        <span>Subject</span>
        <span>Customer</span>
        <span>Status</span>
        <span className="sm:text-right">Updated</span>
      </div>
      {tickets.map((ticket) => (
        <button
          key={ticket.id}
          type="button"
          onClick={() => onOpen(ticket)}
          className={cn(
            GRID,
            "px-3 py-2.5 text-left transition-colors hover:bg-accent/60 focus-visible:bg-accent focus-visible:outline-none",
          )}
        >
          <span className="truncate text-sm font-medium">{ticket.subject}</span>
          <span className="truncate text-xs text-muted-foreground">{ticket.customer_email}</span>
          <span className="justify-self-start sm:justify-self-auto">
            <StatusBadge status={ticket.status} />
          </span>
          <span className="text-xs text-muted-foreground tabular-nums sm:text-right">
            {formatDate(ticket.updated_at)}
          </span>
        </button>
      ))}
    </div>
  )
}
