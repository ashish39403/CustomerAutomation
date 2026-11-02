import { useQuery } from "@tanstack/react-query"
import { useEffect, useRef, useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { Search } from "lucide-react"
import { Pagination } from "@/components/Pagination"
import { TicketTable } from "@/components/TicketTable"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { REFRESH_MS } from "@/lib/constants"
import { fetchTickets } from "@/lib/api"
import { PAGE_SIZE, TICKET_FILTER_VALUES } from "@/lib/tickets"
import type { TicketFilterValue } from "@/lib/types"
import { cn } from "cn"

const FILTER_LABELS: Record<TicketFilterValue, string> = {
  all: "All",
  auto_replied: "Auto-replied",
  handed_off: "Handed off",
  pending: "Pending",
}

function readStatusParam(raw: string | null): TicketFilterValue {
  return TICKET_FILTER_VALUES.includes(raw as TicketFilterValue)
    ? (raw as TicketFilterValue)
    : "all"
}

function readPageParam(raw: string | null): number {
  const page = Number(raw ?? "1")
  return Number.isInteger(page) && page > 0 ? page : 1
}

/** 300ms debounce so typing does not hammer the server search. */
function useDebounced(value: string, delayMs: number): string {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delayMs)
    return () => window.clearTimeout(timer)
  }, [value, delayMs])
  return debounced
}

export function TicketsPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const status = readStatusParam(searchParams.get("status"))
  const search = searchParams.get("q") ?? ""
  const rawPage = readPageParam(searchParams.get("page"))
  const debouncedSearch = useDebounced(search, 300)

  function updateParams(update: { status?: TicketFilterValue; q?: string; page?: number }) {
    const next = new URLSearchParams(searchParams)
    if (update.status !== undefined) {
      if (update.status === "all") {
        next.delete("status")
      } else {
        next.set("status", update.status)
      }
      next.delete("page")
    }
    if (update.q !== undefined) {
      if (update.q === "") {
        next.delete("q")
      } else {
        next.set("q", update.q)
      }
      next.delete("page")
    }
    if (update.page !== undefined) {
      if (update.page <= 1) {
        next.delete("page")
      } else {
        next.set("page", String(update.page))
      }
    }
    setSearchParams(next, { replace: true })
  }

  // When the filter or the debounced search changes, drop back to page 1 —
  // but never on mount, so deep links like ?page=3 survive.
  const previous = useRef({ status, search: debouncedSearch })
  useEffect(() => {
    if (previous.current.status !== status || previous.current.search !== debouncedSearch) {
      previous.current = { status, search: debouncedSearch }
      updateParams({ page: 1 })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, debouncedSearch])

  // Server-side pagination and search: the backend owns the query parameters.
  const ticketsQuery = useQuery({
    queryKey: ["tickets", status, rawPage, debouncedSearch],
    queryFn: () =>
      fetchTickets({
        status,
        page: rawPage,
        page_size: PAGE_SIZE,
        q: debouncedSearch !== "" ? debouncedSearch : undefined,
      }),
    refetchInterval: REFRESH_MS,
  })

  const data = ticketsQuery.data
  const pageCount = Math.max(1, data?.pages ?? 1)
  const page = Math.min(rawPage, pageCount)

  const firstLoad = ticketsQuery.isPending && data === undefined

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-2.5 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-sm font-semibold">Tickets</h1>
        <div className="w-full sm:w-64">
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="search"
              value={search}
              placeholder="Search email or subject…"
              className="h-8 pl-8"
              onChange={(event) => updateParams({ q: event.target.value })}
            />
          </div>
        </div>
      </div>

      <div
        aria-label="Filter by status"
        className="flex gap-1 overflow-x-auto rounded-lg border bg-card p-1"
      >
        {TICKET_FILTER_VALUES.map((value) => (
          <button
            key={value}
            type="button"
            aria-pressed={status === value}
            onClick={() => updateParams({ status: value })}
            className={cn(
              "whitespace-nowrap rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
              status === value
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-accent hover:text-foreground",
            )}
          >
            {FILTER_LABELS[value]}
          </button>
        ))}
      </div>

      <Card className="overflow-hidden py-0">
        <TicketTable
          tickets={data?.items ?? []}
          loading={firstLoad}
          error={data === undefined ? (ticketsQuery.error ?? null) : null}
          onRetry={() => void ticketsQuery.refetch()}
          onOpen={(ticket) => navigate(`/tickets/${ticket.id}`)}
          emptyTitle={data === undefined || data.total === 0 ? "No tickets yet" : "No tickets match"}
          emptyHint={
            data === undefined || data.total === 0
              ? "Customer conversations appear here once the Gmail poller runs."
              : "Try a different status or search term."
          }
        />
        <div className="border-t">
          <Pagination
            page={page}
            pageCount={pageCount}
            onPageChange={(next) => updateParams({ page: next })}
          />
        </div>
      </Card>

      {!firstLoad && !ticketsQuery.isError && (
        <p className="px-1 text-[11px] text-muted-foreground tabular-nums">
          {data?.total ?? "—"} ticket{(data?.total ?? 0) === 1 ? "" : "s"}
          {data !== undefined && data.pages > 1 ? ` · page ${page} of ${data.pages}` : ""}
          {ticketsQuery.isFetching ? " · refreshing…" : ""}
        </p>
      )}
    </div>
  )
}
