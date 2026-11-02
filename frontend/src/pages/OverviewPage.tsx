import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { Bot, Inbox, UserRoundCheck, Zap } from "lucide-react"
import { StatCard } from "@/components/StatCard"
import { SystemStatus } from "@/components/SystemStatus"
import { JobTable } from "@/components/JobTable"
import { TicketTable } from "@/components/TicketTable"
import { UnavailableState } from "@/components/states"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { REFRESH_MS } from "@/lib/constants"
import { fetchJobs, fetchStats, fetchTickets, isNotImplemented, retryJob } from "@/lib/api"
import type { JobListItem, Ticket } from "@/lib/types"

export function OverviewPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // --- support pipeline (operational once the ticket phase lands) ---
  const statsQuery = useQuery({
    queryKey: ["stats"],
    queryFn: fetchStats,
    refetchInterval: REFRESH_MS,
  })
  const ticketsQuery = useQuery({
    queryKey: ["tickets", "all", "overview"],
    queryFn: () => fetchTickets({ page_size: 8 }),
    refetchInterval: REFRESH_MS,
  })

  // --- real operational data, wired to the live backend ---
  const jobsQuery = useQuery({
    queryKey: ["jobs", "overview"],
    queryFn: () => fetchJobs({ limit: 12 }),
    refetchInterval: REFRESH_MS,
  })

  const retryMutation = useMutation({
    mutationFn: (job: JobListItem) => retryJob(job.id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["jobs"] })
    },
  })

  const stats = statsQuery.data

  const statsBlocked = statsQuery.isError && isNotImplemented(statsQuery.error)

  function openTicket(ticket: Ticket) {
    navigate(`/tickets/${ticket.id}`)
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-baseline justify-between gap-3">
        <h1 className="text-sm font-semibold">Overview</h1>
        <p className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
          <span className="size-1.5 animate-pulse rounded-full bg-emerald-500" />
          Live — refreshes every {REFRESH_MS / 1000}s
        </p>
      </div>

      {statsBlocked ? (
        <Card>
          <UnavailableState endpoint="GET /api/stats" phase="ticket pipeline" className="py-8" />
        </Card>
      ) : (
        <div className="grid grid-cols-2 gap-2.5 xl:grid-cols-4">
          <StatCard
            label="Auto-replied"
            value={stats?.auto_replied}
            icon={<Zap />}
            tone="ok"
            hint="Resolved by the AI"
          />
          <StatCard
            label="Handed off"
            value={stats?.handed_off}
            icon={<UserRoundCheck />}
            tone="warn"
            hint="Needs a human"
          />
          <StatCard
            label="Pending"
            value={stats?.pending}
            icon={<Bot />}
            tone="info"
            hint="Awaiting triage"
          />
          <StatCard
            label="Total today"
            value={stats?.today_total}
            icon={<Inbox />}
            tone="neutral"
            hint="All handled today"
          />
        </div>
      )}

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)]">
        <SystemStatus />
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Recent jobs</CardTitle>
            <CardDescription className="text-xs">
              Background work — Gmail poller, pipeline runs, sends
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <JobTable
              jobs={jobsQuery.data?.items ?? []}
              loading={jobsQuery.isPending}
              error={jobsQuery.error ?? null}
              onRetryQuery={() => void jobsQuery.refetch()}
              onRetryJob={(job) => retryMutation.mutate(job)}
              retryingJobId={retryMutation.isPending ? (retryMutation.variables?.id ?? null) : null}
            />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Recent tickets</CardTitle>
          <CardDescription className="text-xs">
            Newest first — open one to read the thread
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {ticketsQuery.isPending ? (
            <div className="flex flex-col gap-2 p-3" aria-busy="true">
              {Array.from({ length: 5 }, (_, index) => (
                <Skeleton key={index} className="h-9 w-full" />
              ))}
            </div>
          ) : (
            <TicketTable
              tickets={ticketsQuery.data?.items ?? []}
              loading={false}
              error={ticketsQuery.error ?? null}
              onRetry={() => void ticketsQuery.refetch()}
              onOpen={openTicket}
              emptyTitle="No tickets yet"
              emptyHint="Customer conversations appear here once the Gmail poller runs."
            />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
