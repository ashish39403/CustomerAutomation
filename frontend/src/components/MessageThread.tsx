import { EmptyState } from "./ui/States"
import { formatDate } from "../lib/format"
import type { MessageAuthor, TicketMessage } from "../lib/types"
import { cn } from "../lib/cn"

const AUTHOR_LABELS: Record<MessageAuthor, string> = {
  customer: "Customer",
  bot: "Bot",
  human: "Agent",
}

function bubbleClasses(author: MessageAuthor): string {
  switch (author) {
    case "customer":
      return "border-line bg-surface"
    case "bot":
      return "border-accent/20 bg-accent-soft"
    case "human":
      return "ml-auto border-accent/30 bg-accent text-accent-fg"
  }
}

export function MessageThread({ messages, className }: { messages: TicketMessage[]; className?: string }) {
  if (messages.length === 0) {
    return (
      <EmptyState
        title="No messages yet"
        hint="This ticket does not have any messages."
        className={className}
      />
    )
  }

  // Thread order: oldest first, ties broken by id.
  const ordered = [...messages].sort((a, b) => {
    const byDate = Date.parse(a.created_at) - Date.parse(b.created_at)
    return Number.isNaN(byDate) ? a.id - b.id : byDate || a.id - b.id
  })

  return (
    <ol className={cn("flex min-h-64 flex-col gap-2.5", className)}>
      {ordered.map((message) => (
        <li
          key={message.id}
          className={cn(
            "flex flex-col",
            message.author === "human" ? "items-end" : "items-stretch sm:pr-12",
          )}
        >
          <div
            className={cn(
              "max-w-[85%] rounded-lg border px-3 py-2 text-sm",
              bubbleClasses(message.author),
            )}
          >
            <p
              className={cn(
                "mb-0.5 text-[11px] font-medium",
                message.author === "human" ? "text-accent-fg/75" : "text-muted-fg",
              )}
            >
              {AUTHOR_LABELS[message.author]} · {formatDate(message.created_at)}
            </p>
            <p className="whitespace-pre-wrap break-words">{message.body}</p>
          </div>
        </li>
      ))}
    </ol>
  )
}
