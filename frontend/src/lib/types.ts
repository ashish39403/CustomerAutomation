/** Types for the backend API contract. Do not change these paths/fields lightly. */

export type TicketStatus = "auto_replied" | "handed_off" | "pending"

/** Filter values used by the tickets list: the three statuses plus "all". */
export type TicketFilterValue = TicketStatus | "all"

/** GET /api/stats — note the backend never awards auto_replied (auto-send is off). */
export interface StatsResponse {
  auto_replied: number
  handed_off: number
  pending: number
  today_total: number
}

/** One ticket from GET /api/tickets. The id is a UUID string. */
export interface Ticket {
  id: string
  customer_email: string
  subject: string
  status: string
  created_at: string
  updated_at: string
}

/** Envelope of GET /api/tickets — pagination happens on the server. */
export interface TicketListEnvelope {
  items: Ticket[]
  total: number
  page: number
  page_size: number
  pages: number
}

/** Who sent a message in the thread. */
export type MessageAuthor = "customer" | "bot" | "human"

export interface TicketMessage {
  id: string
  author: MessageAuthor
  body: string
  created_at: string
}

/** GET /api/tickets/{id}: the ticket plus its full message thread. */
export interface TicketDetail extends Ticket {
  messages: TicketMessage[]
  /** Bot reasoning and classification, shown when the backend returns them. */
  classification?: string | null
  reasoning?: string | null
}

/** Reply and draft: the backend answers with the new thread message. */
export type ReplyResponse = TicketMessage

/** POST /api/tickets/{id}/escalate|resolve|reopen|assign */
export interface TicketActionResponse {
  id: string
  status: string
  assigned_to: string | null
}

/** PATCH /api/tickets/{id}/draft */
export interface DraftResponse {
  ticket_id: string
  body: string
  updated_at: string
}

export type UserRole = "admin" | "operator"

/** GET /api/auth/me — the user object is NOT wrapped in {user}. */
export interface UserSummary {
  id: string
  email: string
  display_name: string
  role: UserRole
}

/** POST /api/auth/login — this response wraps the user in {user}. */
export interface LoginSuccess {
  user: UserSummary
}

/** One row of GET /api/jobs */
export type JobStatus = "queued" | "running" | "succeeded" | "retry_wait" | "dead"

export interface JobListItem {
  id: string
  job_type: string
  status: JobStatus
  attempts: number
  max_attempts: number
  payload_json: Record<string, unknown> | null
  last_error: string | null
  available_at: string
  locked_by: string | null
  locked_until: string | null
  created_at: string
  updated_at: string
}

/** GET /api/jobs */
export interface JobListResponse {
  items: JobListItem[]
  total: number
}

/** GET /api/gmail/status — admin only. */
export interface GmailStatus {
  connected: boolean
  email: string | null
  status: string | null
  last_error: string | null
}

/** GET /health/ready */
export interface ReadinessComponent {
  status: string
  detail: string | null
}

export interface ReadinessStatus {
  status: string
  database: ReadinessComponent
  qdrant: ReadinessComponent
  gmail: ReadinessComponent
}

/** One row of GET /api/documents (knowledge base) */
export interface DocumentItem {
  id: string
  title: string
  object_key: string
  mime_type: string
  size_bytes: number
  checksum: string | null
  version: number
  status: string
  created_at: string
  indexed_at: string | null
}

/** GET /api/documents */
export interface DocumentListResponse {
  items: DocumentItem[]
}
