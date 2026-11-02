import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import {
  ApiError,
  fetchMe,
  fetchJobs,
  fetchTicket,
  fetchTickets,
  fetchStats,
  login,
  normalizeJob,
  normalizeJobList,
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
  it("fetchStats sends a GET with credentials under /api", async () => {
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

  it("login posts the email identity under /api/auth/login", async () => {
    const unauthorized = vi.fn()
    setUnauthorizedHandler(unauthorized)
    const fetchMock = mockFetch(async () =>
      jsonResponse({ user: { id: "u1", email: "admin@local", display_name: "admin", role: "admin" } }),
    )

    const result = await login("admin", "secret")

    expect(result.user.email).toBe("admin@local")
    expect(unauthorized).not.toHaveBeenCalled()
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe(`${BASE}/api/auth/login`)
    expect(init.method).toBe("POST")
    expect(JSON.parse(init.body as string)).toEqual({ email: "admin", password: "secret" })
  })

  it("fetchMe probes the session without triggering a logout", async () => {
    const unauthorized = vi.fn()
    setUnauthorizedHandler(unauthorized)
    const fetchMock = mockFetch(async () => jsonResponse({}, 401))

    await expect(fetchMe()).rejects.toBeInstanceOf(ApiError)
    expect(unauthorized).toHaveBeenCalledTimes(1)
    const [url] = fetchMock.mock.calls[0] as [string]
    expect(url).toBe(`${BASE}/api/auth/me`)
  })

  it("fetchJobs builds query params and unwraps the envelope", async () => {
    const jobRow = {
      id: "11111111-2222-3333-4444-555555555555",
      job_type: "gmail_poll",
      status: "queued",
      attempts: 0,
      max_attempts: 3,
      payload_json: {},
      last_error: null,
      available_at: "2026-01-02T10:00:00Z",
      locked_by: null,
      locked_until: null,
      created_at: "2026-01-02T10:00:00Z",
      updated_at: "2026-01-02T10:00:00Z",
    }
    const fetchMock = mockFetch(async () =>
      jsonResponse({ items: [jobRow], total: 1 }),
    )

    const result = await fetchJobs({ status: "dead", limit: 12 })

    expect(result).toEqual({ items: [normalizeJob(jobRow)], total: 1 })
    const [url] = fetchMock.mock.calls[0] as [string]
    expect(url).toBe(`${BASE}/api/jobs?status=dead&limit=12`)
  })

  it("fetchTickets builds status and page query params", async () => {
    const fetchMock = mockFetch(async () => jsonResponse([ticket]))

    await fetchTickets({ status: "pending", page: 2 })

    const [url] = fetchMock.mock.calls[0] as [string]
    expect(url).toBe(`${BASE}/api/tickets?status=pending&page=2`)
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
  it("normalizes a job row", () => {
    const job = normalizeJob({
      id: "abc",
      job_type: "gmail_poll",
      status: "running",
      attempts: 2,
      max_attempts: 5,
      payload_json: { a: 1 },
      last_error: null,
      available_at: "2026-01-01T00:00:00Z",
      locked_by: "worker-1",
      locked_until: "2026-01-01T00:01:00Z",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:30Z",
    })

    expect(job).toMatchObject({ id: "abc", job_type: "gmail_poll", status: "running", attempts: 2 })
  })

  it("coerces unknown job statuses to queued", () => {
    expect(normalizeJob({ id: "x", status: "weird" }).status).toBe("queued")
  })

  it("unwraps both array and enveloped job lists", () => {
    expect(normalizeJobList([{ id: "a" }]).total).toBe(1)
    expect(normalizeJobList({ items: [{ id: "a" }], total: 7 }).total).toBe(7)
  })

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
