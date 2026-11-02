import { describe, expect, it } from "vitest"
import {
  PAGE_SIZE,
  filterTickets,
  matchesSearch,
  pageCount,
  paginate,
  sortByUpdatedDesc,
} from "./tickets"
import type { Ticket, TicketStatus } from "./types"

function makeTicket(
  id: number,
  status: TicketStatus = "pending",
  subject = `Ticket ${id}`,
  email = `user${id}@example.com`,
  updated_at = "2026-01-01T00:00:00Z",
): Ticket {
  return {
    id: String(id),
    status,
    subject,
    customer_email: email,
    created_at: updated_at,
    updated_at,
  }
}

const tickets: Ticket[] = [
  makeTicket(1, "auto_replied", "Pump is missing", "amy@example.com", "2026-01-03T09:00:00Z"),
  makeTicket(2, "handed_off", "Cracked panel 4", "bob@example.com", "2026-01-02T09:00:00Z"),
  makeTicket(3, "pending", "Which size for 90 kg?", "cat@example.com", "2026-01-01T09:00:00Z"),
]

describe("matchesSearch", () => {
  it("matches the subject, case-insensitively", () => {
    expect(matchesSearch(tickets[0], "pump")).toBe(true)
    expect(matchesSearch(tickets[0], "PUMP")).toBe(true)
  })

  it("matches the customer email", () => {
    expect(matchesSearch(tickets[1], "bob@")).toBe(true)
    expect(matchesSearch(tickets[1], "amy")).toBe(false)
  })

  it("ignores whitespace and empty queries match everything", () => {
    expect(matchesSearch(tickets[0], "   ")).toBe(true)
    expect(matchesSearch(tickets[0], " missing ")).toBe(true)
    expect(matchesSearch(tickets[2], "refun")).toBe(false)
  })
})

describe("filterTickets", () => {
  it("filters by status", () => {
    const result = filterTickets(tickets, { status: "handed_off" })
    expect(result.map((ticket) => ticket.id)).toEqual(["2"])
  })

  it("returns everything for all/none", () => {
    expect(filterTickets(tickets, { status: "all" })).toHaveLength(3)
    expect(filterTickets(tickets, {})).toHaveLength(3)
  })

  it("combines status and search", () => {
    const result = filterTickets(tickets, { status: "pending", search: "cat@example" })
    expect(result.map((ticket) => ticket.id)).toEqual(["3"])
    expect(filterTickets(tickets, { status: "pending", search: "panel" })).toHaveLength(0)
  })
})

describe("sortByUpdatedDesc", () => {
  it("puts the newest ticket first", () => {
    const sorted = sortByUpdatedDesc([tickets[2], tickets[0], tickets[1]])
    expect(sorted.map((ticket) => ticket.id)).toEqual(["1", "2", "3"])
  })
})

describe("paginate", () => {
  it("slices the requested page with the default page size", () => {
    const many = Array.from({ length: 25 }, (_, index) => makeTicket(index + 1))
    expect(paginate(many, 1)).toHaveLength(PAGE_SIZE)
    expect(paginate(many, 2)).toHaveLength(PAGE_SIZE)
    expect(paginate(many, 3)).toHaveLength(25 - 2 * PAGE_SIZE)
    expect(paginate(many, 4)).toHaveLength(0)
  })

  it("clamps invalid pages to page 1", () => {
    expect(paginate(tickets, 0)).toEqual(tickets.slice(0, PAGE_SIZE))
    expect(paginate(tickets, -3).map((ticket) => ticket.id)).toEqual(["1", "2", "3"])
  })
})

describe("pageCount", () => {
  it("covers every item, at least one page", () => {
    expect(pageCount(0)).toBe(1)
    expect(pageCount(1)).toBe(1)
    expect(pageCount(PAGE_SIZE)).toBe(1)
    expect(pageCount(PAGE_SIZE + 1)).toBe(2)
    expect(pageCount(25)).toBe(3)
  })
})
