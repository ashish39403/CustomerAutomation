import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState, type KeyboardEvent } from "react"
import { ApiError, postReply } from "../lib/api"
import type { TicketDetail } from "../lib/types"
import { Spinner } from "./ui/Spinner"
import { SendIcon } from "./ui/icons"
import { Textarea } from "./ui/Input"

export interface ReplyBoxProps {
  ticket: TicketDetail
  onClose?: () => void
}

export function ReplyBox({ ticket, onClose }: ReplyBoxProps) {
  const [text, setText] = useState("")
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: (body: string) => postReply(ticket.id, body),
    onSuccess: () => {
      setText("")
      void queryClient.invalidateQueries({ queryKey: ["ticket", ticket.id] })
      void queryClient.invalidateQueries({ queryKey: ["tickets"] })
      void queryClient.invalidateQueries({ queryKey: ["stats"] })
    },
  })

  function send() {
    const trimmed = text.trim()
    if (trimmed === "" || mutation.isPending) {
      return
    }
    mutation.mutate(trimmed)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      send()
    }
    if (event.key === "Escape") {
      setText("")
      onClose?.()
    }
  }

  const error =
    mutation.error instanceof ApiError
      ? mutation.error.message
      : mutation.error
        ? "Sending the reply failed. Please try again."
        : null

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        send()
      }}
      className="rounded-lg border border-line bg-surface focus-within:border-accent"
    >
      <Textarea
        bare
        rows={4}
        value={text}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Type a reply to the customer…"
        className="min-h-24 resize-y"
      />
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-2.5 py-2">
        <p className="text-[11px] text-muted-fg">
          Enter to send · Shift+Enter for a new line · Esc to clear
        </p>
        {error && <p className="text-xs text-red-500">{error}</p>}
        <div className="flex items-center gap-2">
          {mutation.isSuccess && !mutation.isPending && text === "" && (
            <p className="text-xs text-emerald-600 dark:text-emerald-400">Reply sent</p>
          )}
          <button
            type="submit"
            disabled={text.trim() === "" || mutation.isPending}
            className="inline-flex h-8 items-center gap-1.5 rounded-md bg-accent px-3 text-xs font-medium text-accent-fg transition-colors hover:bg-accent/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:pointer-events-none disabled:opacity-50"
          >
            {mutation.isPending ? (
              <Spinner className="size-3.5 text-accent-fg" />
            ) : (
              <SendIcon className="size-3.5" />
            )}
            {mutation.isPending ? "Sending…" : "Send reply"}
          </button>
        </div>
      </div>
    </form>
  )
}
