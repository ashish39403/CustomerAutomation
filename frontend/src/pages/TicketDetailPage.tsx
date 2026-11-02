import { useEffect, useState } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { MessageThread } from "../components/MessageThread"
import { ReplyBox } from "../components/ReplyBox"
import { StatusBadge } from "../components/ui/StatusBadge"
import { ErrorState, LoadingState } from "../components/ui/States"
import { ChevronDownIcon, SparklesIcon } from "../components/ui/icons"
import { REFRESH_MS } from "../lib/constants"
import { fetchTicket } from "../lib/api"
import { formatDate } from "../lib/format"

/** Collapsible panel with the bot's reasoning; Esc closes it. */
function ReasoningPanel({ reasoning }: { reasoning: string }) {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!open) {
      return
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false)
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [open])

  return (
    <div className="rounded-lg border border-line bg-surface">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
        className="flex w-full items-center gap-2 px-2.5 py-2 text-left text-xs font-medium text-muted-fg transition-colors hover:text-fg"
      >
        <SparklesIcon className="size-3.5" />
        Bot reasoning
        <ChevronDownIcon
          className={`ml-auto transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <p className="whitespace-pre-wrap break-words border-t border-line px-2.5 py-2.5 text-xs leading-relaxed text-muted-fg">
          {reasoning}
        </p>
      )}
    </div>
  )
}

export function TicketDetailPage() {
  const params = useParams()
  const navigate = useNavigate()
  const ticketId = Number(params.id)

  const ticketQuery = useQuery({
    queryKey: ["ticket", ticketId],
    queryFn: () => fetchTicket(ticketId),
    enabled: Number.isInteger(ticketId) && ticketId > 0,
    refetchInterval: REFRESH_MS,
  })

  if (!Number.isInteger(ticketId) || ticketId <= 0) {
    return (
      <ErrorState
        message={`"${params.id}" is not a valid ticket id.`}
        onRetry={() => void navigate("/tickets")}
      />
    )
  }

  const ticket = ticketQuery.data

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <Link
          to="/tickets"
          className="inline-flex items-center gap-1.5 text-sm text-muted-fg transition-colors hover:text-fg"
        >
          Tickets
        </Link>
        {ticket && (
          <p className="text-[11px] text-muted-fg tabular-nums">
            #{ticket.id} · updated {formatDate(ticket.updated_at)}
          </p>
        )}
      </div>

      {ticketQuery.isPending ? (
        <LoadingState label="Loading ticket…" />
      ) : ticketQuery.isError ? (
        <div className="rounded-lg border border-line bg-surface">
          <ErrorState
            message={
              ticketQuery.error instanceof Error
                ? ticketQuery.error.message
                : "Failed to load the ticket"
            }
            onRetry={() => void ticketQuery.refetch()}
          />
        </div>
      ) : ticket && (
        <>
          <div className="flex flex-col gap-2 rounded-lg border border-line bg-surface p-3">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="mr-auto text-base font-semibold">{ticket.subject}</h1>
              <StatusBadge status={ticket.status} />
              {ticket.classification && (
                <span className="inline-flex items-center gap-1 rounded-full border border-line bg-soft px-2 py-0.5 text-[11px] font-medium text-muted-fg">
                  Classified: {ticket.classification}
                </span>
              )}
            </div>
            <p className="truncate text-xs text-muted-fg">{ticket.customer_email}</p>
          </div>

          {ticket.reasoning && <ReasoningPanel reasoning={ticket.reasoning} />}

          <div className="rounded-lg border border-line bg-surface p-3">
            <MessageThread messages={ticket.messages} className="max-h-[60vh] overflow-y-auto" />
          </div>

          <div className="flex flex-col gap-1.5">
            <h2 className="text-sm font-semibold">Reply to customer</h2>
            <ReplyBox ticket={ticket} />
          </div>
        </>
      )}
    </div>
  )
}
