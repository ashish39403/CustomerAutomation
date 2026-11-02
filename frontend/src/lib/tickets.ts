import type { Ticket, TicketFilterValue } from "./types"

/**
 * Pure ticket list logic: search, status filtering, sorting and pagination.
 * Kept free of React so it is trivial to unit test.
 */

export const PAGE_SIZE = 10

export const TICKET_FILTER_VALUES: readonly TicketFilterValue[] = [
  "all",
  "auto_replied",
  "handed_off",
  "pending",
]

export function matchesSearch(ticket: Ticket, rawSearch: string): boolean {
  const query = rawSearch.trim().toLowerCase()
  if (query === "") {
    return true
  }
  return (
    ticket.customer_email.toLowerCase().includes(query) ||
    ticket.subject.toLowerCase().includes(query)
  )
}

export function filterTickets(
  tickets: Ticket[],
  filter: { status?: TicketFilterValue; search?: string },
): Ticket[] {
  return tickets.filter((ticket) => {
    const statusOk =
      filter.status === undefined || filter.status === "all" || ticket.status === filter.status
    return statusOk && matchesSearch(ticket, filter.search ?? "")
  })
}

/** Newest first; ties broken by id so the order is stable. */
export function sortByUpdatedDesc(tickets: Ticket[]): Ticket[] {
  return [...tickets].sort((a, b) => {
    const byDate = Date.parse(b.updated_at) - Date.parse(a.updated_at)
    return Number.isNaN(byDate) ? 0 : byDate || (a.id > b.id ? -1 : a.id < b.id ? 1 : 0)
  })
}

export function paginate<T>(items: T[], page: number, pageSize = PAGE_SIZE): T[] {
  const safePage = Math.max(1, Math.floor(page) || 1)
  const start = (safePage - 1) * pageSize
  return items.slice(start, start + pageSize)
}

export function pageCount(totalItems: number, pageSize = PAGE_SIZE): number {
  return Math.max(1, Math.ceil(totalItems / pageSize))
}
