import { useEffect, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Link, useNavigate, useParams } from "react-router-dom"
import { ArrowLeft, ChevronDown, Sparkles } from "lucide-react"
import { MessageThread } from "@/components/MessageThread"
import { ReplyBox } from "@/components/ReplyBox"
import { StatusBadge } from "@/components/status-badge"
import { ErrorState } from "@/components/states"
import {
  Card,
  CardContent,
  CardTitle,
} from "@/components/ui/card"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { REFRESH_MS } from "@/lib/constants"
import { fetchTicket, isNotImplemented } from "@/lib/api"
import { apiErrorMessage } from "@/lib/api"
import { formatDate } from "@/lib/format"
import { cn } from "cn"

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
    <Collapsible open={open} onOpenChange={setOpen}>
      <div className="rounded-lg border bg-card">
        <CollapsibleTrigger className="flex w-full items-center gap-2 px-2.5 py-2 text-left text-xs font-medium text-muted-foreground transition-colors hover:text-foreground">
          <Sparkles className="size-3.5" />
          Bot reasoning
          <ChevronDown
            className={cn("ml-auto transition-transform", open ? "rotate-180" : "")}
          />
        </CollapsibleTrigger>
        <CollapsibleContent>
          <p className="whitespace-pre-wrap break-words border-t px-2.5 py-2.5 text-xs leading-relaxed text-muted-foreground">
            {reasoning}
          </p>
        </CollapsibleContent>
      </div>
    </Collapsible>
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
    retry: (failureCount, error) => !isNotImplemented(error) && failureCount < 1,
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
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" />
          Tickets
        </Link>
        {ticket && (
          <p className="text-[11px] text-muted-foreground tabular-nums">
            #{ticket.id} · updated {formatDate(ticket.updated_at)}
          </p>
        )}
      </div>

      {ticket === undefined ? (
        <Card>
          <div className="p-4">
            <ErrorState
              message={
                isNotImplemented(ticketQuery.error)
                  ? "The ticket pipeline is not part of the backend yet."
                  : apiErrorMessage(ticketQuery.error)
              }
              onRetry={() => void ticketQuery.refetch()}
            />
          </div>
        </Card>
      ) : (
        <>
          <Card>
            <CardContent className="flex flex-col gap-1.5 px-3 py-3 sm:flex-row sm:items-start sm:gap-3">
              <div className="min-w-0 flex-1">
                <CardTitle className="truncate text-sm font-semibold sm:text-base">
                  {ticket.subject}
                </CardTitle>
                <p className="mt-0.5 truncate text-xs text-muted-foreground">
                  {ticket.customer_email}
                </p>
              </div>
              <div className="flex shrink-0 flex-wrap items-center gap-2">
                <StatusBadge status={ticket.status} />
                {ticket.classification && (
                  <span className="inline-flex items-center gap-1 rounded-full border bg-secondary px-2 py-0.5 text-[11px] font-medium text-secondary-foreground">
                    Classified: {ticket.classification}
                  </span>
                )}
              </div>
            </CardContent>
          </Card>

          {ticket.reasoning && <ReasoningPanel reasoning={ticket.reasoning} />}

          <Card>
            <CardContent className="p-3">
              <MessageThread
                messages={ticket.messages}
                className="max-h-[60vh] overflow-y-auto"
              />
            </CardContent>
          </Card>

          <div className="flex flex-col gap-1.5">
            <h2 className="text-sm font-semibold">Reply to customer</h2>
            <ReplyBox ticket={ticket} />
          </div>
        </>
      )}
    </div>
  )
}
