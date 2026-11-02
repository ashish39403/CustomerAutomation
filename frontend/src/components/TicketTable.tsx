import { StatusBadge } from "./ui/StatusBadge"
import { EmptyState, ErrorState } from "./ui/States"
import { formatDate } from "../lib/format"
import type { Ticket } from "../lib/types"
import { cn } from "../lib/cn"

export interface TicketTableProps {
  tickets: Ticket[]
  loading?: boolean
  error?: string | null
  onRetry?: () => void
  onOpen: (ticket: Ticket) => void
  emptyTitle?: string
  emptyHint?: string
  className?: string
}

const GRID =
  "grid grid-cols-1 gap-1 sm:grid-cols-[minmax(0,2fr)_minmax(0,1.6fr)_120px_130px] sm:items-center"

export function TicketTable({
  tickets,
  loading = false,
  error = null,
  onRetry,
  onOpen,
  emptyTitle = "No tickets",
  emptyHint,
  className,
}: TicketTableProps) {
  if (error) {
    return <ErrorState message={error} onRetry={onRetry} className={className} />
  }

  if (loading) {
    return (
      <div className={cn("flex flex-col", className)} aria-busy="true">
        {Array.from({ length: 6 }, (_, index) => (
          <div key={index} className={cn(GRID, "border-b border-line px-3 py-2.5")}>
            <div className="h-4 w-3/5 animate-pulse rounded bg-soft" />
            <div className="h-3.5 w-2/5 animate-pulse rounded bg-soft" />
            <div className="h-4 w-20 animate-pulse rounded-full bg-soft" />
            <div className="h-3.5 w-24 animate-pulse rounded bg-soft" />
          </div>
        ))}
      </div>
    )
  }

  if (tickets.length === 0) {
    return (
      <EmptyState
        title={emptyTitle}
        hint={emptyHint}
        className={className}
      />
    )
  }

  return (
    <div className={cn("flex flex-col", className)}>
      <div
        className={cn(
          GRID,
          "hidden border-b border-line px-3 pb-2 text-[11px] font-medium uppercase tracking-wide text-muted-fg sm:grid",
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
            "border-b border-line px-3 py-2.5 text-left transition-colors last:border-0 hover:bg-soft/60 focus-visible:bg-soft focus-visible:outline-none",
          )}
        >
          <span className="truncate text-sm font-medium">{ticket.subject}</span>
          <span className="truncate text-xs text-muted-fg">{ticket.customer_email}</span>
          <span className="justify-self-start sm:justify-self-auto">
            <StatusBadge status={ticket.status} />
          </span>
          <span className="text-xs text-muted-fg tabular-nums sm:text-right">
            {formatDate(ticket.updated_at)}
          </span>
        </button>
      ))}
    </div>
  )
}
