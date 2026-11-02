import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { formatDate } from "@/lib/format"
import type { MessageAuthor, TicketMessage } from "@/lib/types"
import { cn } from "cn"

const AUTHOR_LABELS: Record<MessageAuthor, string> = {
  customer: "Customer",
  bot: "Bot",
  human: "Agent",
}

function bubbleClasses(author: MessageAuthor): string {
  switch (author) {
    case "customer":
      return "border-border bg-card"
    case "bot":
      return "border-primary/20 bg-primary/10 dark:border-primary/30"
    case "human":
      return "ml-auto border-primary/30 bg-primary text-primary-foreground"
  }
}

export function MessageThread({
  messages,
  className,
}: {
  messages: TicketMessage[]
  className?: string
}) {
  if (messages.length === 0) {
    return (
      <Empty className={cn("py-12", className)}>
        <EmptyHeader>
          <EmptyTitle>No messages yet</EmptyTitle>
          <EmptyDescription>This ticket does not have any messages.</EmptyDescription>
        </EmptyHeader>
      </Empty>
    )
  }

  // Thread order: oldest first, ties broken by id.
  const ordered = [...messages].sort((a, b) => {
    const byDate = Date.parse(a.created_at) - Date.parse(b.created_at)
    return Number.isNaN(byDate) ? 0 : byDate || (a.id > b.id ? 1 : a.id < b.id ? -1 : 0)
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
                message.author === "human" ? "text-primary-foreground/75" : "text-muted-foreground",
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
