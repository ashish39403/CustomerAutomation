/** Types for the backend API contract. Do not change these paths/fields lightly. */

export type TicketStatus = "auto_replied" | "handed_off" | "pending"

/** Filter values used by the tickets list: the three statuses plus "all". */
export type TicketFilterValue = TicketStatus | "all"

/** GET /api/stats */
export interface StatsResponse {
  auto_replied: number
  handed_off: number
  pending: number
}

/** One ticket from GET /api/tickets */
export interface Ticket {
  id: number
  customer_email: string
  subject: string
  status: TicketStatus
  updated_at: string
}

/** Who sent a message in the thread. */
export type MessageAuthor = "customer" | "bot" | "human"

export interface TicketMessage {
  id: number
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

/** POST /api/auth/login. The session itself lives in an HttpOnly cookie. */
export type LoginResponse = Record<string, unknown> | null

export type UserRole = "admin" | "operator"

/** GET /api/auth/me */
export interface UserSummary {
  id: string
  email: string
  display_name: string
  role: UserRole
}

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

/** GET /api/gmail/status */
export interface GmailStatus {
  connected: boolean
  email: string | null
  status: string | null
  last_error: string | null
}

/** GET /api/health/ready */
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

/** POST /api/tickets/{id}/reply */
export interface ReplyResponse {
  ok?: boolean
  message?: TicketMessage
}
