import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import {
  ApiError,
  fetchTicket,
  fetchTickets,
  fetchStats,
  login,
  normalizeMessage,
  normalizeTicketDetail,
  postReply,
  setUnauthorizedHandler,
} from "./api"
import type { TicketDetail } from "./types"

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  })
}

const BASE = "https://api.example.com"

function mockFetch(handler: (url: string, init?: RequestInit) => Promise<Response>) {
  const mock = vi.fn(handler)
  vi.stubGlobal("fetch", mock)
  return mock
}

const ticket = {
  id: 3,
  customer_email: "jane@example.com",
  subject: "Where is my pump?",
  status: "pending",
  updated_at: "2026-01-02T10:00:00Z",
}

beforeEach(() => {
  vi.stubEnv("VITE_API_URL", BASE)
})

afterEach(() => {
  setUnauthorizedHandler(null)
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
})

describe("api client", () => {
  it("fetchStats sends a GET with credentials to the configured base URL", async () => {
    const fetchMock = mockFetch(async () =>
      jsonResponse({ auto_replied: 4, handed_off: 2, pending: 1 }),
    )

    const stats = await fetchStats()

    expect(stats).toEqual({ auto_replied: 4, handed_off: 2, pending: 1 })
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe(`${BASE}/api/stats`)
    expect(init.method).toBeUndefined()
    expect(init.credentials).toBe("include")
  })

  it("fetchTickets builds status and page query params", async () => {
    const fetchMock = mockFetch(async () => jsonResponse([ticket]))

    await fetchTickets({ status: "pending", page: 2 })

    const [url] = fetchMock.mock.calls[0] as [string]
    expect(url).toBe(`${BASE}/api/tickets?status=pending&page=2`)
  })

  it('fetchTickets omits params for status "all"', async () => {
    const fetchMock = mockFetch(async () => jsonResponse([ticket]))

    await fetchTickets({ status: "all" })

    const [url] = fetchMock.mock.calls[0] as [string]
    expect(url).toBe(`${BASE}/api/tickets`)
  })

  it("login posts JSON credentials and does not fire the 401 handler", async () => {
    const unauthorized = vi.fn()
    setUnauthorizedHandler(unauthorized)
    const fetchMock = mockFetch(async () => jsonResponse({}, 401))

    await expect(login("admin", "secret")).rejects.toMatchObject({
      name: "ApiError",
      status: 401,
    })

    expect(unauthorized).not.toHaveBeenCalled()
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe(`${BASE}/api/auth/login`)
    expect(init.method).toBe("POST")
    expect(JSON.parse(init.body as string)).toEqual({ username: "admin", password: "secret" })
  })

  it("a 401 elsewhere fires the unauthorized handler", async () => {
    const unauthorized = vi.fn()
    setUnauthorizedHandler(unauthorized)
    mockFetch(async () => jsonResponse({}, 401))

    await expect(fetchStats()).rejects.toBeInstanceOf(ApiError)
    expect(unauthorized).toHaveBeenCalledTimes(1)
  })

  it("surfaces the FastAPI error detail on failure", async () => {
    mockFetch(async () => jsonResponse({ detail: "Ticket not found" }, 404))

    const error = await fetchTicket(999).catch((caught: unknown) => caught)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(404)
    expect((error as ApiError).message).toBe("Ticket not found")
  })

  it("maps a network failure to a reachable error", async () => {
    mockFetch(async () => {
      throw new TypeError("offline")
    })

    const error = await fetchStats().catch((caught: unknown) => caught)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(0)
    expect((error as ApiError).message).toContain("Network error")
  })

  it("postReply sends the reply body", async () => {
    const fetchMock = mockFetch(async () => jsonResponse({ ok: true }))

    await postReply(7, "Replacement shipped")

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe(`${BASE}/api/tickets/7/reply`)
    expect(init.method).toBe("POST")
    expect(JSON.parse(init.body as string)).toEqual({ body: "Replacement shipped" })
  })
})

describe("normalizers", () => {
  it("maps author aliases to the MessageAuthor contract", () => {
    expect(
      normalizeMessage({ id: 1, role: "customer", body: "Need help", created_at: "2026-01-01" }),
    ).toMatchObject({ author: "customer" })
    expect(
      normalizeMessage({ id: 2, direction: "in", body: "Need help", created_at: "" }),
    ).toMatchObject({ author: "customer" })
    expect(
      normalizeMessage({ id: 3, author: "bot", body: "Ships tomorrow", created_at: "" }),
    ).toMatchObject({ author: "bot" })
    expect(
      normalizeMessage({ id: 4, role: "agent", body: "Fixed", created_at: "" }),
    ).toMatchObject({ author: "human" })
  })

  it("accepts the thread under messages or thread and optional reasoning", () => {
    const raw = {
      ...ticket,
      thread: [{ id: 1, role: "customer", body: "Need help", created_at: "2026-01-01" }],
      reasoning: "Stock levels checked",
      classification: "shipping",
    }

    const detail: TicketDetail = normalizeTicketDetail(raw)

    expect(detail.messages).toHaveLength(1)
    expect(detail.messages[0]).toMatchObject({ author: "customer", body: "Need help" })
    expect(detail.reasoning).toBe("Stock levels checked")
    expect(detail.classification).toBe("shipping")
  })
})
