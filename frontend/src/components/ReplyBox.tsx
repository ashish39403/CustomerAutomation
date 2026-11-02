import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState, type KeyboardEvent } from "react"
import { SendHorizontal } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import { apiErrorMessage, postReply } from "@/lib/api"
import type { TicketDetail } from "@/lib/types"

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

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        send()
      }}
      className="flex flex-col gap-2"
    >
      <div className="rounded-lg border border-border bg-card">
        <Textarea
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={handleKeyDown}
          rows={4}
          placeholder="Type a reply to the customer…"
          className="min-h-24 resize-y border-0 shadow-none focus-visible:ring-0 dark:bg-transparent"
        />
        <div className="flex flex-wrap items-center justify-between gap-2 border-t px-2.5 py-2">
          <p className="text-[11px] text-muted-foreground">
            Enter to send · Shift+Enter for a new line · Esc to clear
          </p>
          <Button type="submit" size="sm" disabled={text.trim() === "" || mutation.isPending}>
            {mutation.isPending ? (
              <>
                <Spinner className="text-primary-foreground" />
                Sending…
              </>
            ) : (
              <>
                <SendHorizontal />
                Send reply
              </>
            )}
          </Button>
        </div>
      </div>

      {mutation.isError && (
        <Alert variant="destructive">
          <AlertDescription>{apiErrorMessage(mutation.error)}</AlertDescription>
        </Alert>
      )}
      {mutation.isSuccess && !mutation.isPending && text === "" && (
        <p className="text-xs text-emerald-600 dark:text-emerald-400">Reply sent.</p>
      )}
    </form>
  )
}
