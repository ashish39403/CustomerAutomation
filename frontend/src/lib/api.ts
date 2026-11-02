import type {
  DocumentItem,
  DraftResponse,
  GmailStatus,
  JobListItem,
  JobListResponse,
  LoginSuccess,
  MessageAuthor,
  ReadinessStatus,
  ReplyResponse,
  StatsResponse,
  Ticket,
  TicketActionResponse,
  TicketDetail,
  TicketFilterValue,
  TicketListEnvelope,
  TicketMessage,
  UserSummary,
} from "./types"

/**
 * The one module that talks to the backend. Components never call fetch.
 *
 * The session lives in an HttpOnly cookie set by the API (`ca_session`), so
 * nothing secret is stored or bundled: the only public value is VITE_API_URL.
 *
 * Paths are exactly the ones in CONTRACT.md: `/api/*` for the API and the
 * root-level `/health*` probes. Every endpoint here must match the contract —
 * if code and contract disagree, the contract wins.
 */

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
    // FormData carries its own multipart boundary — never set a Content-Type.
    const headers = { ...(init.headers as Record<string, string>) }
    if (init.body !== undefined && !(init.body instanceof FormData)) {
      headers["Content-Type"] = "application/json"
    }
    response = await fetch(`${apiBaseUrl()}${path}`, {
      ...init,
      credentials: "include",
      headers,
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
 * POST /api/auth/login. The identifier may be an email or a display name
 * (the backend accepts either). Succeeds with a session cookie on any 2xx.
 */
export function login(identifier: string, password: string): Promise<LoginSuccess> {
  return request<LoginSuccess>(
    "/api/auth/login",
    { method: "POST", body: JSON.stringify({ email: identifier, password }) },
    { isLogin: true },
  )
}

/** POST /api/auth/logout — clears the server session. */
export function apiLogout(): Promise<void> {
  return request<void>("/api/auth/logout", { method: "POST" })
}

/** GET /api/auth/me */
export function fetchMe(): Promise<UserSummary> {
  return request<UserSummary>("/api/auth/me")
}

// ------------------------------------------------------------- operations

/** GET /health/ready (root, public) */
export function fetchReadiness(): Promise<ReadinessStatus> {
  return request<ReadinessStatus>("/health/ready")
}

/** GET /api/gmail/status */
export function fetchGmailStatus(): Promise<GmailStatus> {
  return request<GmailStatus>("/api/gmail/status")
}

/**
 * URL of GET /api/gmail/connect — a server-side OAuth redirect, navigated
 * as a full-page load so the browser carries the session cookie.
 */
export function gmailConnectUrl(): string {
  return `${apiBaseUrl()}/api/gmail/connect`
}

export interface JobListParams {
  status?: JobListItem["status"]
  limit?: number
  offset?: number
}

/** GET /api/jobs?status=&limit=&offset= */
export async function fetchJobs(params: JobListParams = {}): Promise<JobListResponse> {
  const search = new URLSearchParams()
  if (params.status !== undefined) search.set("status", params.status)
  if (params.limit !== undefined) search.set("limit", String(params.limit))
  if (params.offset !== undefined) search.set("offset", String(params.offset))
  const query = search.toString()
  const raw: unknown = await request<unknown>(`/api/jobs${query ? `?${query}` : ""}`)
  return normalizeJobList(raw)
}

/** POST /api/jobs/{id}/retry (admin only) */
export function retryJob(id: string): Promise<JobListItem> {
  return request<JobListItem>(`/api/jobs/${id}/retry`, { method: "POST" })
}

// --------------------------------------------------- ticket pipeline

/** GET /api/stats */
export function fetchStats(): Promise<StatsResponse> {
  return request<StatsResponse>("/api/stats")
}

export interface TicketListParams {
  status?: TicketFilterValue
  page?: number
  page_size?: number
  /** Server-side search over customer email and subject. */
  q?: string
}

/** GET /api/tickets?status=&page=&page_size=&q= — paginated on the server. */
export async function fetchTickets(params: TicketListParams = {}): Promise<TicketListEnvelope> {
  const search = new URLSearchParams()
  if (params.status && params.status !== "all") search.set("status", params.status)
  if (params.page !== undefined) search.set("page", String(params.page))
  if (params.page_size !== undefined) search.set("page_size", String(params.page_size))
  if (params.q !== undefined && params.q.trim() !== "") search.set("q", params.q.trim())
  const query = search.toString()
  const raw: unknown = await request<unknown>(`/api/tickets${query ? `?${query}` : ""}`)
  return normalizeTicketList(raw)
}

/** GET /api/tickets/{id} — the full message thread. */
export async function fetchTicket(id: string): Promise<TicketDetail> {
  const raw: unknown = await request<unknown>(`/api/tickets/${encodeURIComponent(id)}`)
  return normalizeTicketDetail(raw)
}

/** POST /api/tickets/{id}/reply — sends a human reply to the customer. */
export function postReply(id: string, body: string): Promise<ReplyResponse> {
  return request<ReplyResponse>(`/api/tickets/${encodeURIComponent(id)}/reply`, {
    method: "POST",
    body: JSON.stringify({ body }),
  })
}

/** PATCH /api/tickets/{id}/draft — stores (or replaces) the operator draft. */
export function patchDraft(id: string, body: string): Promise<DraftResponse> {
  return request<DraftResponse>(`/api/tickets/${encodeURIComponent(id)}/draft`, {
    method: "PATCH",
    body: JSON.stringify({ body }),
  })
}

/** POST /api/tickets/{id}/escalate | /resolve | /reopen */
export function ticketAction(
  action: "escalate" | "resolve" | "reopen",
  id: string,
): Promise<TicketActionResponse> {
  return request<TicketActionResponse>(`/api/tickets/${encodeURIComponent(id)}/${action}`, {
    method: "POST",
  })
}

/** POST /api/tickets/{id}/assign — assigns the ticket to another user. */
export function assignTicket(id: string, assignedTo: string | null): Promise<TicketActionResponse> {
  return request<TicketActionResponse>(`/api/tickets/${encodeURIComponent(id)}/assign`, {
    method: "POST",
    body: JSON.stringify({ assigned_to: assignedTo }),
  })
}

// ------------------------------------------------- knowledge base documents

/** GET /api/documents */
export async function fetchDocuments(): Promise<DocumentItem[]> {
  const raw: unknown = await request<unknown>("/api/documents")
  return normalizeDocumentList(raw)
}

/**
 * POST /api/documents (admin) — multipart upload. The file field must be
 * named exactly `file`; `replaceId` bumps an existing document's version.
 */
export function uploadDocument(file: File, replaceId?: string): Promise<DocumentItem> {
  const form = new FormData()
  form.append("file", file)
  if (replaceId !== undefined) form.append("replace_id", replaceId)
  return request<DocumentItem>("/api/documents", { method: "POST", body: form })
}

/** DELETE /api/documents/{id} (admin) — queues the document for deletion. */
export function deleteDocument(id: string): Promise<DocumentItem> {
  return request<DocumentItem>(`/api/documents/${encodeURIComponent(id)}`, { method: "DELETE" })
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

export function normalizeTicketList(raw: unknown): TicketListEnvelope {
  const data = asRecord(raw)
  // Tolerate a bare array as well as the envelope.
  if (Array.isArray(raw)) {
    return {
      items: raw.map(normalizeTicket),
      total: raw.length,
      page: 1,
      page_size: raw.length,
      pages: 1,
    }
  }
  const items = asArray(data.items ?? data.tickets ?? data.results)
  return {
    items: items.map(normalizeTicket),
    total: typeof data.total === "number" ? data.total : items.length,
    page: typeof data.page === "number" ? data.page : 1,
    page_size: typeof data.page_size === "number" ? data.page_size : items.length,
    pages: typeof data.pages === "number" ? data.pages : 1,
  }
}

export function normalizeTicket(raw: unknown): Ticket {
  const data = asRecord(raw)
  return {
    id: String(data.id ?? ""),
    customer_email: String(data.customer_email ?? data.email ?? ""),
    subject: String(data.subject ?? "(no subject)"),
    status: toStatus(data.status),
    created_at: String(data.created_at ?? ""),
    updated_at: String(data.updated_at ?? ""),
  }
}

export function normalizeMessage(raw: unknown): TicketMessage {
  const data = asRecord(raw)
  return {
    id: String(data.id ?? ""),
    author: toAuthor(data.author ?? data.role ?? data.sender ?? data.direction),
    body: String(data.body ?? data.content ?? ""),
    created_at: String(data.created_at ?? ""),
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

export function normalizeDocumentList(raw: unknown): DocumentItem[] {
  if (Array.isArray(raw)) {
    return raw.map(normalizeDocument)
  }
  const data = asRecord(raw)
  return asArray(data.items ?? data.documents ?? data.results).map(normalizeDocument)
}

export function normalizeDocument(raw: unknown): DocumentItem {
  const data = asRecord(raw)
  return {
    id: String(data.id ?? ""),
    title: String(data.title ?? "(untitled)"),
    object_key: String(data.object_key ?? ""),
    mime_type: String(data.mime_type ?? ""),
    size_bytes: Number(data.size_bytes ?? 0),
    checksum: typeof data.checksum === "string" ? data.checksum : null,
    version: Number(data.version ?? 1),
    status: String(data.status ?? "unknown"),
    created_at: String(data.created_at ?? ""),
    indexed_at: typeof data.indexed_at === "string" ? data.indexed_at : null,
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
