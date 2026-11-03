from enum import StrEnum


class UserRole(StrEnum):
    OPERATOR = "operator"
    ADMIN = "admin"


class GmailAccountStatus(StrEnum):
    CONNECTED = "connected"
    EXPIRED = "expired"
    NEEDS_REAUTHORIZATION = "needs_reauthorization"
    DISCONNECTED = "disconnected"


class TicketStatus(StrEnum):
    NEW = "new"
    PROCESSING = "processing"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REPLIED = "replied"
    AUTO_REPLIED = "auto_replied"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    FAILED = "failed"


class TicketCategory(StrEnum):
    ORDER_STATUS = "order_status"
    SHIPPING = "shipping"
    RETURNS = "returns"
    REFUND = "refund"
    PRODUCT_QUESTION = "product_question"
    DAMAGED_ITEM = "damaged_item"
    MISSING_ITEM = "missing_item"
    PAYMENT = "payment"
    COMPLAINT = "complaint"
    OTHER = "other"


class TicketPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class MessageDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class DocumentStatus(StrEnum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"
    DELETING = "deleting"
    DELETED = "deleted"


class JobType(StrEnum):
    POLL_GMAIL = "poll_gmail"
    PROCESS_EMAIL = "process_email"
    INDEX_DOCUMENT = "index_document"
    DELETE_DOCUMENT = "delete_document"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    RETRY_WAIT = "retry_wait"
    DEAD = "dead"


class SendAttemptStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    UNKNOWN = "unknown"


class Decision(StrEnum):
    NEEDS_REVIEW = "needs_review"
    ESCALATE = "escalate"
    AUTO_SEND = "auto_send"
    NO_REPLY = "no_reply"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ActorType(StrEnum):
    USER = "user"
    SYSTEM = "system"
    WORKER = "worker"
