import { useQuery } from "@tanstack/react-query"
import { useMemo } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { Pagination } from "../components/Pagination"
import { TicketTable } from "../components/TicketTable"
import { Input } from "../components/ui/Input"
import { SearchIcon } from "../components/ui/icons"
import { REFRESH_MS } from "../lib/constants"
import { cn } from "../lib/cn"
import { fetchTickets } from "../lib/api"
import { useDebouncedValue } from "../lib/hooks"
import {
  TICKET_FILTER_VALUES,
  filterTickets,
  pageCount,
  paginate,
  sortByUpdatedDesc,
} from "../lib/tickets"
import type { TicketFilterValue } from "../lib/types"

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

export function TicketsPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const status = readStatusParam(searchParams.get("status"))
  const search = searchParams.get("q") ?? ""
  const rawPage = Number(searchParams.get("page") ?? "1")
  const page = Number.isInteger(rawPage) && rawPage > 0 ? rawPage : 1

  const debouncedSearch = useDebouncedValue(search, 250)

  const ticketsQuery = useQuery({
    queryKey: ["tickets", status],
    queryFn: () => fetchTickets(status === "all" ? {} : { status }),
    refetchInterval: REFRESH_MS,
  })

  const filtered = useMemo(() => {
    const data = ticketsQuery.data ?? []
    return sortByUpdatedDesc(filterTickets(data, { status, search: debouncedSearch }))
  }, [ticketsQuery.data, status, debouncedSearch])

  const total = pageCount(filtered.length)
  const currentPage = Math.min(page, total)
  const paged = useMemo(
    () => paginate(filtered, currentPage),
    [filtered, currentPage],
  )

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

  const data = ticketsQuery.data ?? []
  const isStaleLoading = ticketsQuery.isPending && ticketsQuery.fetchStatus !== "idle"

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-2.5 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-sm font-semibold">Tickets</h2>
        <div className="flex items-center gap-2">
          <div className="relative w-full sm:w-64">
            <SearchIcon className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-fg" />
            <Input
              type="search"
              value={search}
              placeholder="Search email or subject…"
              className="pl-8"
              onChange={(event) => updateParams({ q: event.target.value })}
            />
          </div>
        </div>
      </div>

      <div
        aria-label="Filter by status"
        className="flex gap-1 overflow-x-auto rounded-lg border border-line bg-surface p-1"
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
                ? "bg-accent text-accent-fg"
                : "text-muted-fg hover:bg-soft hover:text-fg",
            )}
          >
            {FILTER_LABELS[value]}
          </button>
        ))}
      </div>

      <div className="overflow-hidden rounded-lg border border-line bg-surface">
        <TicketTable
          tickets={paged}
          loading={isStaleLoading}
          error={
            ticketsQuery.isError && data.length === 0
              ? ticketsQuery.error instanceof Error
                ? ticketsQuery.error.message
                : "Failed to load tickets"
              : null
          }
          onRetry={() => void ticketsQuery.refetch()}
          onOpen={(ticket) => navigate(`/tickets/${ticket.id}`)}
          emptyTitle={
            data.length === 0 ? "No tickets yet" : "No tickets match"
          }
          emptyHint={
            data.length === 0
              ? "New customer emails will show up here automatically."
              : "Try a different status or search term."
          }
        />
        <Pagination
          page={currentPage}
          pageCount={total}
          onPageChange={(next) => updateParams({ page: next })}
        />
      </div>

      {!isStaleLoading && !ticketsQuery.isError && (
        <p className="px-1 text-[11px] text-muted-fg">
          {filtered.length} ticket{filtered.length === 1 ? "" : "s"}
          {search !== "" || status !== "all" ? ` · ${data.length} total` : ""}
        </p>
      )}
    </div>
  )
}
