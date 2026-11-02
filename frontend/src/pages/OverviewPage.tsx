import { useQuery } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { StatCard } from "../components/StatCard"
import { TicketTable } from "../components/TicketTable"
import { Button } from "../components/ui/Button"
import { ErrorState } from "../components/ui/States"
import {
  BotReplyIcon,
  ClockIcon,
  HandOffIcon,
  InboxIcon,
} from "../components/ui/icons"
import { REFRESH_MS } from "../lib/constants"
import { fetchStats, fetchTickets } from "../lib/api"
import { sortByUpdatedDesc } from "../lib/tickets"
import type { Ticket } from "../lib/types"

const RECENT_COUNT = 8

export function OverviewPage() {
  const navigate = useNavigate()

  const statsQuery = useQuery({
    queryKey: ["stats"],
    queryFn: fetchStats,
    refetchInterval: REFRESH_MS,
  })

  const ticketsQuery = useQuery({
    queryKey: ["tickets", "all", "overview"],
    queryFn: () => fetchTickets(),
    refetchInterval: REFRESH_MS,
    select: sortByUpdatedDesc,
  })

  const stats = statsQuery.data
  const todayTotal: number | undefined =
    stats === undefined
      ? undefined
      : stats.auto_replied + stats.handed_off + stats.pending

  function openTicket(ticket: Ticket) {
    navigate(`/tickets/${ticket.id}`)
  }

  const statsError =
    statsQuery.error instanceof Error ? statsQuery.error.message : "Failed to load stats"
  const ticketsError =
    ticketsQuery.error instanceof Error ? ticketsQuery.error.message : "Failed to load tickets"

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="text-sm font-semibold">Overview</h2>
        <p className="flex items-center gap-1.5 text-[11px] text-muted-fg">
          <span className="size-1.5 animate-pulse rounded-full bg-emerald-500" />
          Live — refreshes every {REFRESH_MS / 1000}s
        </p>
      </div>

      {statsQuery.isError ? (
        <div className="rounded-lg border border-line bg-surface">
          <ErrorState message={statsError} onRetry={() => void statsQuery.refetch()} />
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-2.5 xl:grid-cols-4">
          <StatCard
            label="Auto-replied"
            value={stats?.auto_replied}
            icon={<BotReplyIcon />}
            tone="ok"
            hint="Resolved by the AI"
          />
          <StatCard
            label="Handed off"
            value={stats?.handed_off}
            icon={<HandOffIcon />}
            tone="warn"
            hint="Needs a human"
          />
          <StatCard
            label="Pending"
            value={stats?.pending}
            icon={<ClockIcon />}
            tone="info"
            hint="Awaiting triage"
          />
          <StatCard
            label="Total today"
            value={todayTotal}
            icon={<InboxIcon />}
            tone="neutral"
            hint="All handled today"
          />
        </div>
      )}

      <section className="flex flex-col gap-2">
        <div className="flex items-baseline justify-between gap-3">
          <h3 className="text-sm font-semibold">Recent tickets</h3>
          <Button variant="ghost" size="sm" onClick={() => navigate("/tickets")}>
            View all
          </Button>
        </div>
        <div className="overflow-hidden rounded-lg border border-line bg-surface">
          <TicketTable
            tickets={(ticketsQuery.data ?? []).slice(0, RECENT_COUNT)}
            loading={ticketsQuery.isPending && ticketsQuery.fetchStatus !== "idle"}
            error={ticketsQuery.isError ? ticketsError : null}
            onRetry={() => void ticketsQuery.refetch()}
            onOpen={openTicket}
            emptyTitle="No tickets yet"
            emptyHint="New customer emails will show up here automatically."
            className="h-full"
          />
        </div>
        <p className="px-1 text-[11px] text-muted-fg">
          Showing the {RECENT_COUNT} most recent of {(ticketsQuery.data ?? []).length} tickets,
          newest first
        </p>
      </section>
    </div>
  )
}
