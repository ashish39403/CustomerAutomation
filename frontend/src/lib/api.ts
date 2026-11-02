import type {
  GmailStatus,
  JobListItem,
  JobListResponse,
  LoginSuccess,
  MessageAuthor,
  ReadinessStatus,
  ReplyResponse,
  StatsResponse,
  Ticket,
  TicketDetail,
  TicketFilterValue,
  TicketMessage,
  UserSummary,
} from "./types"

/**
 * The one module that talks to the backend. Components never call fetch.
 *
 * The session lives in an HttpOnly cookie set by the API (`ca_session`), so
 * nothing secret is stored or bundled: the only public value is VITE_API_URL.
 *
 * The backend serves everything under /api/v1. The ticket pipeline endpoints
 * (stats / tickets / reply) are part of the dashboard contract and come online
 * with a later backend phase; until then they answer 404 and the pages render
 * a friendly "not available yet" state.
 */

const API_PREFIX = "/api/v1"

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

type UnauthorizedHandler = () => void

let onUnauthorized: UnauthorizedHandler | null = null

/** Register (or clear) the callback fired when the API answers 401. */
export function setUnauthorizedHandler(handler: UnauthorizedHandler | null): void {
  onUnauthorized = handler
}

function apiBaseUrl(): string {
  const raw = import.meta.env.VITE_API_URL
  return (raw ?? "").replace(/\/+$/, "")
}

interface RequestOptions {
  /** A 401 on the login call means wrong credentials, not a lost session. */
  isLogin?: boolean
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  options: RequestOptions = {},
): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${apiBaseUrl()}${API_PREFIX}${path}`, {
      ...init,
      credentials: "include",
      headers: {
        ...(init.body === undefined ? {} : { "Content-Type": "application/json" }),
        ...init.headers,
      },
    })
  } catch {
    throw new ApiError(0, "Network error — could not reach the API")
  }

  if (response.status === 401 && !options.isLogin) {
    onUnauthorized?.()
  }

  if (!response.ok) {
    throw new ApiError(response.status, await errorMessage(response))
  }

  const text = await response.text()
  if (text === "") {
    return undefined as T
  }
  try {
    return JSON.parse(text) as T
  } catch {
    throw new ApiError(0, "The API returned an unexpected response")
  }
}

async function errorMessage(response: Response): Promise<string> {
  const fallback = `Request failed with status ${response.status}`
  try {
    const data: unknown = JSON.parse(await response.text())
    if (data !== null && typeof data === "object" && "detail" in data) {
      const detail = (data as { detail?: unknown }).detail
      if (typeof detail === "string" && detail.trim() !== "") {
        return detail
      }
    }
  } catch {
    // Not JSON — use the fallback message.
  }
  return fallback
}

/** Turn an unknown error into a short message for a page-level error state. */
export function apiErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.status === 0 ? error.message : `${error.message} (HTTP ${error.status})`
  }
  return error instanceof Error && error.message !== ""
    ? error.message
    : "Something went wrong"
}

/** True when the endpoint does not exist on the backend yet (later phase). */
export function isNotImplemented(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404
}

// ---------------------------------------------------------------- auth

/**
 * POST /api/v1/auth/login. The identifier may be an email or a display name
 * (the backend accepts either). Succeeds with a session cookie on any 2xx.
 */
export function login(identifier: string, password: string): Promise<LoginSuccess> {
  return request<LoginSuccess>(
    "/auth/login",
    { method: "POST", body: JSON.stringify({ email: identifier, password }) },
    { isLogin: true },
  )
}

/** POST /api/v1/auth/logout — clears the server session. */
export function apiLogout(): Promise<void> {
  return request<void>("/auth/logout", { method: "POST" })
}

/** GET /api/v1/auth/me */
export function fetchMe(): Promise<UserSummary> {
  return request<UserSummary>("/auth/me")
}

// ------------------------------------------------------------- operations

/** GET /api/v1/health/ready */
export function fetchReadiness(): Promise<ReadinessStatus> {
  return request<ReadinessStatus>("/health/ready")
}

/** GET /api/v1/gmail/status */
export function fetchGmailStatus(): Promise<GmailStatus> {
  return request<GmailStatus>("/gmail/status")
}

export interface JobListParams {
  status?: JobListItem["status"]
  limit?: number
  offset?: number
}

/** GET /api/v1/jobs?status=&limit=&offset= */
export async function fetchJobs(params: JobListParams = {}): Promise<JobListResponse> {
  const search = new URLSearchParams()
  if (params.status !== undefined) search.set("status", params.status)
  if (params.limit !== undefined) search.set("limit", String(params.limit))
  if (params.offset !== undefined) search.set("offset", String(params.offset))
  const query = search.toString()
  const raw: unknown = await request<unknown>(`/jobs${query ? `?${query}` : ""}`)
  return normalizeJobList(raw)
}

/** POST /api/v1/jobs/{id}/retry (admin only) */
export function retryJob(id: string): Promise<JobListItem> {
  return request<JobListItem>(`/jobs/${id}/retry`, { method: "POST" })
}

// -------------------------------------------- ticket pipeline (later phase)

/** GET /api/v1/stats */
export function fetchStats(): Promise<StatsResponse> {
  return request<StatsResponse>("/stats")
}

export interface TicketListParams {
  status?: TicketFilterValue
  page?: number
}

/** GET /api/v1/tickets?status=&page= */
export async function fetchTickets(params: TicketListParams = {}): Promise<Ticket[]> {
  const search = new URLSearchParams()
  if (params.status && params.status !== "all") search.set("status", params.status)
  if (params.page !== undefined) search.set("page", String(params.page))
  const query = search.toString()
  const raw: unknown = await request<unknown>(`/tickets${query ? `?${query}` : ""}`)
  return normalizeTicketList(raw)
}

/** GET /api/v1/tickets/{id} — the full message thread. */
export async function fetchTicket(id: number | string): Promise<TicketDetail> {
  const raw: unknown = await request<unknown>(`/tickets/${id}`)
  return normalizeTicketDetail(raw)
}

/** POST /api/v1/tickets/{id}/reply — sends a human reply to the customer. */
export function postReply(id: number | string, body: string): Promise<ReplyResponse> {
  return request<ReplyResponse>(`/tickets/${id}/reply`, {
    method: "POST",
    body: JSON.stringify({ body }),
  })
}

// ------------------------------------------------------------ normalizers
// Small anti-corruption layer: components consume the typed contract, while
// harmless differences in the response are smoothed out here.

function asRecord(raw: unknown): Record<string, unknown> {
  return typeof raw === "object" && raw !== null ? (raw as Record<string, unknown>) : {}
}

function asArray(raw: unknown): unknown[] {
  return Array.isArray(raw) ? raw : []
}

export function normalizeJobList(raw: unknown): JobListResponse {
  if (Array.isArray(raw)) {
    return { items: raw.map(normalizeJob), total: raw.length }
  }
  const data = asRecord(raw)
  const items = asArray(data.items ?? data.jobs ?? data.results)
  return {
    items: items.map(normalizeJob),
    total: typeof data.total === "number" ? data.total : items.length,
  }
}

export function normalizeJob(raw: unknown): JobListItem {
  const data = asRecord(raw)
  const statusValue = typeof data.status === "string" ? data.status : "queued"
  const status: JobListItem["status"] = (
    ["queued", "running", "succeeded", "retry_wait", "dead"] as const
  ).includes(statusValue as JobListItem["status"])
    ? (statusValue as JobListItem["status"])
    : "queued"
  return {
    id: String(data.id ?? ""),
    job_type: String(data.job_type ?? data.type ?? "job"),
    status,
    attempts: Number(data.attempts ?? 0),
    max_attempts: Number(data.max_attempts ?? 1),
    payload_json:
      typeof data.payload_json === "object" && data.payload_json !== null
        ? (data.payload_json as Record<string, unknown>)
        : null,
    last_error: typeof data.last_error === "string" ? data.last_error : null,
    available_at: String(data.available_at ?? ""),
    locked_by: typeof data.locked_by === "string" ? data.locked_by : null,
    locked_until: typeof data.locked_until === "string" ? data.locked_until : null,
    created_at: String(data.created_at ?? ""),
    updated_at: String(data.updated_at ?? ""),
  }
}

export function normalizeTicketList(raw: unknown): Ticket[] {
  if (Array.isArray(raw)) {
    return raw.map(normalizeTicket)
  }
  // Tolerate enveloped responses like { items: [...] }.
  const container = asRecord(raw)
  const inner = asArray(container.items ?? container.tickets ?? container.results)
  return inner.map(normalizeTicket)
}

export function normalizeTicket(raw: unknown): Ticket {
  const data = asRecord(raw)
  return {
    id: Number(data.id ?? 0),
    customer_email: String(data.customer_email ?? data.email ?? ""),
    subject: String(data.subject ?? "(no subject)"),
    status: toStatus(data.status),
    updated_at: String(data.updated_at ?? ""),
  }
}

export function normalizeTicketDetail(raw: unknown): TicketDetail {
  const data = asRecord(raw)
  const thread = asArray(data.messages ?? data.thread)
  return {
    ...normalizeTicket(data),
    messages: thread.map(normalizeMessage),
    classification: optionalText(data.classification),
    reasoning: optionalText(data.reasoning),
  }
}

export function normalizeMessage(raw: unknown): TicketMessage {
  const data = asRecord(raw)
  return {
    id: Number(data.id ?? 0),
    author: toAuthor(data.author ?? data.role ?? data.sender ?? data.direction),
    body: String(data.body ?? data.content ?? ""),
    created_at: String(data.created_at ?? ""),
  }
}

function toStatus(value: unknown): Ticket["status"] {
  if (typeof value === "string") {
    // Unknown values are passed through; the badge renders them neutrally.
    return value.trim().toLowerCase() as Ticket["status"]
  }
  return "pending"
}

function toAuthor(value: unknown): MessageAuthor {
  if (typeof value !== "string") {
    return "human"
  }
  switch (value.trim().toLowerCase()) {
    case "customer":
    case "in":
    case "inbound":
      return "customer"
    case "bot":
    case "ai":
    case "auto":
    case "assistant":
      return "bot"
    default:
      return "human"
  }
}

function optionalText(value: unknown): string | null {
  return typeof value === "string" && value.trim() !== "" ? value : null
}
