# Product Requirements Document (PRD)
## AI E-commerce Customer Support Automation

**Status:** Draft for implementation  
**Product type:** Internal tool for one e-commerce company  
**Primary users:** Customer-support operators and support manager  
**Version:** 1.0

---

## 1. Product summary

Build an internal support-automation system that connects to one company's Gmail support inbox, ingests customer emails, classifies and prioritizes them, retrieves relevant company policies and product information, and proposes safe, grounded replies.

The system must not let an LLM independently decide to send sensitive or uncertain responses. Deterministic backend rules decide whether a reply can be sent automatically, should wait for human approval, or must be escalated.

A React dashboard gives support staff visibility into incoming conversations, AI decisions, draft replies, escalations, and processing history.

## 2. Problem

E-commerce support teams repeatedly answer questions about orders, shipping, returns, refunds, product usage, missing parts, and damaged products. Manual handling is slow and inconsistent. Uncontrolled AI auto-replies create risk, especially for refunds, payments, complaints, and ambiguous cases.

## 3. Goals

1. Reduce repetitive support work using grounded AI drafts and narrowly scoped auto-replies.
2. Keep a complete, auditable record of every email, AI result, human action, and Gmail send.
3. Escalate sensitive, low-confidence, unsupported, or operationally risky cases.
4. Give operators a clear dashboard to review, edit, approve, reject, and resolve tickets.
5. Demonstrate a production-minded end-to-end GenAI system suitable for an engineering internship portfolio.

## 4. Non-goals for V1

- Multi-tenant SaaS or customer-facing subscription/billing.
- Multiple company workspaces or multiple Gmail inboxes.
- Full CRM, order-management, inventory, or payment integrations.
- Autonomous refunds, cancellations, replacements, or changes to customer orders.
- Sending replies without policy checks and audit records.
- Slack/WhatsApp/social-media support channels.
- Complex workflow builder or general-purpose agent platform.
- Training or fine-tuning a foundation model.

## 5. Users and permissions

### Support operator
- View inbox, ticket details, messages, AI classification, evidence, and status.
- Edit AI-generated drafts.
- Approve and send drafts.
- Reject drafts and write a manual reply.
- Assign, escalate, close, and reopen tickets.

### Support manager / administrator
- All operator actions.
- Manage knowledge-base documents and their indexing status.
- Configure conservative automation rules and confidence thresholds.
- View evaluation results, processing failures, and audit history.
- Connect/re-authorize Gmail and manage application settings.

V1 may use a small fixed set of roles. Do not build a generic permissions engine.

## 6. Core user journeys

### 6.1 Connect the support inbox
1. An administrator starts Gmail OAuth.
2. The backend handles the OAuth callback and stores credentials securely.
3. The backend verifies mailbox access and records the connected account.
4. A health indicator shows connected, expired, or needs reauthorization.

### 6.2 Ingest and process a customer email
1. A background poller checks Gmail for new messages at a configured interval.
2. It fetches message/thread metadata and content.
3. The backend normalizes sender, recipients, subject, body, received time, Gmail IDs, and attachments metadata.
4. Idempotency checks prevent duplicate ticket/message creation.
5. The message is persisted before AI processing.
6. A durable job is created in PostgreSQL.
7. The worker classifies the email and runs policy/RAG processing.
8. Deterministic policy code chooses auto-send, approval-required, or escalation.
9. The dashboard updates with the resulting ticket state.

### 6.3 Human review and send
1. An operator opens a ticket and reviews the customer message, AI summary, category, confidence, sources, and risk flags.
2. The operator edits or accepts the draft.
3. The operator explicitly approves sending.
4. The backend rechecks ticket state and send eligibility.
5. The backend sends the reply through Gmail using the correct thread/reply headers.
6. The result and Gmail message ID are persisted.
7. The ticket timeline records who approved and when.

### 6.4 Knowledge-base maintenance
1. An administrator uploads a PDF, TXT, or Markdown policy/product document.
2. The file is stored in Neon Object Storage and its metadata is stored in PostgreSQL.
3. A background ingestion job extracts text, chunks it, embeds chunks, and upserts vectors to Qdrant.
4. The document shows processing, indexed, or failed status.
5. Replacing/deleting a document removes or supersedes its old vectors.
6. Every retrieved chunk links back to its source document and page/section where available.

### 6.5 Handle failures
- Failed Gmail polling is retried with backoff and surfaced in system health.
- Failed AI jobs are retried only for transient failures.
- Permanent failures move to a failed/dead-letter state visible to an administrator.
- Gmail send failures never mark a ticket as replied.
- Retried sends use a send-attempt/idempotency record to avoid accidental duplicate replies.
- Expired OAuth credentials trigger a reauthorization state.

## 7. Functional requirements

### FR-1 Gmail integration
- OAuth 2.0 connection for a dedicated support Gmail account.
- Poll inbox for new messages using Gmail history/sync strategy where practical; support a safe initial backfill.
- Fetch complete thread context needed for a reply.
- Preserve Gmail thread ID and message ID.
- Send replies in the existing thread.
- Handle token refresh, revocation, quota errors, and transient API failures.
- Prevent the automation from processing its own outbound messages as new customer requests.
- Allow configured sender/domain exclusions and internal test addresses.

### FR-2 Ticket and message management
- Create one ticket per customer conversation/thread according to a documented thread-matching rule.
- Store every inbound and outbound message.
- Track ticket status: `new`, `processing`, `needs_review`, `approved`, `replied`, `escalated`, `resolved`, `failed`.
- Track category, priority, risk flags, assignment, and timestamps.
- Maintain an append-only event/audit timeline for important actions.

### FR-3 AI classification
Return validated structured output:
- Category: `order_status`, `shipping`, `returns`, `refund`, `product_question`, `damaged_item`, `missing_item`, `payment`, `complaint`, `other`.
- Short summary.
- Urgency/priority.
- Detected intent and entities where useful.
- Risk flags, including refund/payment/legal/threat/PII/angry-customer indicators.
- Confidence score or calibrated confidence band.

The classifier is advisory. Backend rules remain authoritative.

### FR-4 Knowledge retrieval and answer drafting
- Search Qdrant using the customer query and relevant thread context.
- Apply metadata filters for active documents and document versions.
- Return a bounded set of relevant chunks with source identifiers.
- Draft a concise, empathetic response using only supported facts.
- Include internal citations/source references in the dashboard (not necessarily in the customer-facing email).
- If evidence is insufficient or contradictory, return `insufficient_evidence` and require human handling.
- Never invent order status, refund completion, delivery dates, or actions not verified by an integrated system.

### FR-5 Decision and safety policy
Backend policy code must decide among:
- `auto_send`: only explicitly allowlisted low-risk intents with sufficient evidence and all checks passing.
- `needs_approval`: useful draft exists but human confirmation is required.
- `escalate`: sensitive, risky, unsupported, angry, ambiguous, or operationally consequential case.
- `no_reply`: spam, duplicate, automated notification, or excluded message.

V1 recommended default: **human approval for all AI-generated replies**. Add auto-send only after the evaluation suite demonstrates acceptable performance for a narrow allowlist. Do not enable auto-send merely because the model reports high confidence.

Never auto-send for refunds, payment disputes, cancellations, legal threats, chargebacks, account-security concerns, personal-data requests, or promises requiring live order-system data.

### FR-6 Dashboard
- Login-protected internal dashboard.
- Ticket list with filters for status, category, priority, and date.
- Ticket detail with thread timeline and customer message.
- AI summary, classification, risk flags, retrieved sources, and draft.
- Draft editor with approve/send, reject, and escalate actions.
- Knowledge-base document upload/list/status/delete.
- System health and failed-job view.
- Audit timeline.

### FR-7 Evaluation
- Version-controlled golden dataset of representative support emails.
- Test classification, risk detection, retrieval relevance, answer groundedness, and final policy decision.
- Track regressions when prompts, models, chunking, or policies change.
- Include adversarial emails, prompt-injection attempts, missing evidence, contradictory policies, and duplicate messages.
- Do not use live customer PII in the test dataset.

## 8. Acceptance criteria

V1 is complete when:
1. An administrator can connect a dedicated Gmail inbox.
2. A new inbound email becomes one persisted ticket/message and one durable processing job.
3. Duplicate polling does not create duplicate tickets, messages, or replies.
4. Classification output is schema-validated and visible in the dashboard.
5. The system retrieves relevant knowledge-base chunks and exposes their sources.
6. Unsupported or sensitive cases are routed to human review/escalation.
7. An operator can edit, approve, and send a reply in the original Gmail thread.
8. Send failures are visible and do not falsely mark the ticket as replied.
9. Document upload, indexing, replacement, and deletion work end to end.
10. Every important state transition and human action is auditable.
11. Automated tests cover critical policy, idempotency, and job lifecycle paths.
12. Docker-based deployment and documented setup are reproducible.

## 9. Non-functional requirements

- **Security:** least-privilege Gmail scopes, encrypted secrets, authenticated dashboard/API, strict CORS, input validation, secure uploads, no secrets in logs.
- **Reliability:** idempotent ingestion, durable jobs, bounded retries, explicit failure states.
- **Observability:** structured logs, request/job correlation IDs, job metrics, AI latency/token/cost tracking.
- **Performance:** dashboard list/detail endpoints should be responsive for a small internal team; long AI and indexing tasks run in workers.
- **Maintainability:** modular monolith, typed schemas, migrations, tests, clear service boundaries.
- **Privacy:** store only data needed for support; redact sensitive values from logs; define retention/deletion policy.
- **Recoverability:** database backups and documented restore procedure.

## 10. Suggested V1 limits

- One Gmail mailbox.
- One company knowledge base.
- PDF, TXT, and Markdown documents.
- One embedding model and one chat model behind an OpenAI-compatible API.
- One FastAPI application plus separate worker process from the same codebase.
- PostgreSQL-backed job queue; no Redis/Celery in V1.
- Qdrant as a separate vector service.
- Human approval by default.

## 11. Delivery milestones

1. **Foundation:** repo, settings, logging, migrations, health endpoint, Docker Compose.
2. **Persistence:** tickets, messages, documents, audit events, job tables.
3. **Gmail:** OAuth, token refresh, poller, ingestion, thread reply.
4. **Worker:** durable queue, retries, leases, idempotency.
5. **Knowledge base:** Neon Object Storage upload, extraction, chunking, embeddings, Qdrant retrieval.
6. **AI pipeline:** classification, risk flags, draft generation, deterministic decision policy.
7. **Dashboard:** inbox, ticket detail, draft review, KB management, failed jobs.
8. **Evaluation and hardening:** golden set, security checks, failure tests, deployment docs.

## 12. Product success measures

For a portfolio project, report measured results from the golden dataset and controlled test inbox:
- Classification accuracy / macro-F1.
- Risk-case recall (prioritize catching unsafe cases).
- Retrieval hit rate / Recall@k.
- Percentage of drafts accepted with minor/no edits.
- Unsupported-answer rate.
- Duplicate ingestion/send prevention tests.
- Median and p95 processing latency and estimated cost per processed email.

Do not claim business time savings or production accuracy without real measured evidence.
