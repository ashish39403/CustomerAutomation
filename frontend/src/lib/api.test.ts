import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import {
  ApiError,
  fetchMe,
  fetchDocuments,
  fetchJobs,
  fetchTicket,
  fetchTickets,
  fetchStats,
  login,
  normalizeDocument,
  normalizeDocumentList,
  normalizeJob,
  normalizeJobList,
  normalizeMessage,
  normalizeTicket,
  normalizeTicketDetail,
  normalizeTicketList,
  postReply,
  setUnauthorizedHandler,
  ticketAction,
  uploadDocument,
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

const TICKET_ID = "11111111-2222-3333-4444-555555555555"

const ticketRow = {
  id: TICKET_ID,
  customer_email: "jane@example.com",
  subject: "Where is my pump?",
  status: "pending",
  created_at: "2026-01-01T09:00:00Z",
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
      jsonResponse({ auto_replied: 4, handed_off: 2, pending: 1, today_total: 7 }),
    )

    const stats = await fetchStats()

    expect(stats).toEqual({ auto_replied: 4, handed_off: 2, pending: 1, today_total: 7 })
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

  it("fetchMe tolerates the unwrapped user object", async () => {
    const unauthorized = vi.fn()
    setUnauthorizedHandler(unauthorized)
    const fetchMock = mockFetch(async () =>
      jsonResponse({ id: "u1", email: "admin@local", display_name: "admin", role: "admin" }),
    )

    const me = await fetchMe()

    expect(me.role).toBe("admin")
    expect(unauthorized).not.toHaveBeenCalled()
    expect(fetchMock.mock.calls[0][0]).toBe(`${BASE}/api/auth/me`)
  })

  it("fetchJobs builds query params and unwraps the envelope", async () => {
    const jobRow = {
      id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
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

  it("fetchTickets builds status, page, page_size and q params", async () => {
    const fetchMock = mockFetch(async () =>
      jsonResponse({
        items: [ticketRow],
        total: 11,
        page: 2,
        page_size: 10,
        pages: 2,
      }),
    )

    const envelope = await fetchTickets({
      status: "pending",
      page: 2,
      page_size: 10,
      q: "jane",
    })

    expect(envelope.total).toBe(11)
    expect(envelope.pages).toBe(2)
    expect(envelope.items[0].id).toBe(TICKET_ID)
    const [url] = fetchMock.mock.calls[0] as [string]
    expect(url).toBe(`${BASE}/api/tickets?status=pending&page=2&page_size=10&q=jane`)
  })

  it("fetchTicket and postReply use the UUID string id", async () => {
    const detail = {
      ...ticketRow,
      messages: [
        { id: "cccccccc-0000-1111-2222-333333333333", author: "customer", body: "Hi", created_at: "2026-01-01T09:00:00Z" },
      ],
      classification: "shipping",
      reasoning: "Stock checked",
    }
    mockFetch(async () => jsonResponse(detail))

    const fetched = await fetchTicket(TICKET_ID)
    expect((fetched as TicketDetail).id).toBe(TICKET_ID)

    const fetchMock = mockFetch(async () => jsonResponse(detail.messages[0]))
    await postReply(TICKET_ID, "Replacement shipped")

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe(`${BASE}/api/tickets/${TICKET_ID}/reply`)
    expect(init.method).toBe("POST")
    expect(JSON.parse(init.body as string)).toEqual({ body: "Replacement shipped" })
  })

  it("ticketAction posts to the action path", async () => {
    const fetchMock = mockFetch(async () =>
      jsonResponse({ id: TICKET_ID, status: "handed_off", assigned_to: null }),
    )

    await ticketAction("escalate", TICKET_ID)

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe(`${BASE}/api/tickets/${TICKET_ID}/escalate`)
    expect(init.method).toBe("POST")
  })

  it("uploadDocument sends multipart without a manual content type", async () => {
    const fetchMock = mockFetch(async () => jsonResponse(normalizedDocumentRow()))

    const file = new File(["hello"], "faq.md", { type: "text/markdown" })
    await uploadDocument(file, "dddddddd-0000-1111-2222-333333333333")

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe(`${BASE}/api/documents`)
    expect(init.method).toBe("POST")
    expect(init.body).toBeInstanceOf(FormData)
    const formData = init.body as FormData
    expect(formData.get("file")).toBeInstanceOf(File)
    expect(formData.get("replace_id")).toBe("dddddddd-0000-1111-2222-333333333333")
    const headers = init.headers as Record<string, string>
    expect(headers["Content-Type"]).toBeUndefined()
  })

  it("fetchDocuments unwraps the items array", async () => {
    const fetchMock = mockFetch(async () => jsonResponse({ items: [normalizedDocumentRow()] }))

    const documents = await fetchDocuments()

    expect(documents).toHaveLength(1)
    expect(documents[0].id).toBe("eeeeeeee-1111-2222-3333-444444444444")
    const [url] = fetchMock.mock.calls[0] as [string]
    expect(url).toBe(`${BASE}/api/documents`)
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

    const error = await fetchTicket(TICKET_ID).catch((caught: unknown) => caught)

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
})

function normalizedDocumentRow() {
  return {
    id: "eeeeeeee-1111-2222-3333-444444444444",
    title: "faq.md",
    object_key: "kb/faq.md",
    mime_type: "text/markdown",
    size_bytes: 3203,
    checksum: "abc123",
    version: 2,
    status: "indexed",
    created_at: "2026-01-01T08:00:00Z",
    indexed_at: "2026-01-01T08:01:00Z",
  }
}

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

  it("keeps UUID ticket ids as strings (no NaN coercion)", () => {
    expect(normalizeTicket(ticketRow).id).toBe(TICKET_ID)
    expect(
      normalizeMessage({ id: TICKET_ID, author: "customer", body: "Hi", created_at: "" }).id,
    ).toBe(TICKET_ID)
  })

  it("parses the server pagination envelope and tolerates a bare list", () => {
    const envelope = normalizeTicketList({
      items: [ticketRow],
      total: 11,
      page: 2,
      page_size: 10,
      pages: 2,
    })
    expect(envelope).toMatchObject({ total: 11, page: 2, page_size: 10, pages: 2 })

    const bare = normalizeTicketList([ticketRow])
    expect(bare).toMatchObject({
      items: [expect.objectContaining({ id: TICKET_ID })],
      total: 1,
      pages: 1,
    })
  })

  it("maps author aliases to the MessageAuthor contract", () => {
    expect(
      normalizeMessage({ id: "1", role: "customer", body: "Need help", created_at: "2026-01-01" }),
    ).toMatchObject({ author: "customer" })
    expect(
      normalizeMessage({ id: "2", direction: "in", body: "Need help", created_at: "" }),
    ).toMatchObject({ author: "customer" })
    expect(
      normalizeMessage({ id: "3", author: "bot", body: "Ships tomorrow", created_at: "" }),
    ).toMatchObject({ author: "bot" })
    expect(
      normalizeMessage({ id: "4", role: "agent", body: "Fixed", created_at: "" }),
    ).toMatchObject({ author: "human" })
  })

  it("accepts the thread under messages or thread and optional reasoning", () => {
    const raw = {
      ...ticketRow,
      thread: [{ id: "1", role: "customer", body: "Need help", created_at: "2026-01-01" }],
      reasoning: "Stock levels checked",
      classification: "shipping",
    }

    const detail: TicketDetail = normalizeTicketDetail(raw)

    expect(detail.messages).toHaveLength(1)
    expect(detail.messages[0]).toMatchObject({ author: "customer", body: "Need help" })
    expect(detail.reasoning).toBe("Stock levels checked")
    expect(detail.classification).toBe("shipping")
  })

  it("normalizes documents and unknown statuses", () => {
    const document = normalizeDocument(normalizedDocumentRow())
    expect(document).toMatchObject({ title: "faq.md", version: 2, status: "indexed" })
    expect(normalizeDocument({ id: "x", size_bytes: "5" }).size_bytes).toBe(5)
    expect(normalizeDocumentList({ items: [normalizedDocumentRow()] })).toHaveLength(1)
  })
})
