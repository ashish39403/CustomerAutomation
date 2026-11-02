import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState, type KeyboardEvent } from "react"
import { FileText, SendHorizontal } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import { apiErrorMessage, patchDraft, postReply } from "@/lib/api"
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

  // Saves the text without sending it; the customer never sees a draft.
  const draftMutation = useMutation({
    mutationFn: (body: string) => patchDraft(ticket.id, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["ticket", ticket.id] })
    },
  })

  function send() {
    const trimmed = text.trim()
    if (trimmed === "" || mutation.isPending) {
      return
    }
    mutation.mutate(trimmed)
  }

  function saveDraft() {
    const trimmed = text.trim()
    if (trimmed === "" || draftMutation.isPending) {
      return
    }
    draftMutation.mutate(trimmed)
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

  const busy = mutation.isPending || draftMutation.isPending

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
          <div className="flex items-center gap-1.5">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={text.trim() === "" || busy}
              onClick={saveDraft}
            >
              {draftMutation.isPending ? <Spinner className="size-3.5" /> : <FileText />}
              Save draft
            </Button>
            <Button type="submit" size="sm" disabled={text.trim() === "" || busy}>
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
      </div>

      {mutation.isError && (
        <Alert variant="destructive">
          <AlertDescription>{apiErrorMessage(mutation.error)}</AlertDescription>
        </Alert>
      )}
      {draftMutation.isError && (
        <Alert variant="destructive">
          <AlertDescription>{apiErrorMessage(draftMutation.error)}</AlertDescription>
        </Alert>
      )}
      {draftMutation.isSuccess && !draftMutation.isPending && (
        <p className="text-xs text-emerald-600 dark:text-emerald-400">Draft saved.</p>
      )}
      {mutation.isSuccess && !mutation.isPending && text === "" && (
        <p className="text-xs text-emerald-600 dark:text-emerald-400">Reply sent.</p>
      )}
    </form>
  )
}
