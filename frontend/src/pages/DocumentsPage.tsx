import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useRef } from "react"
import { FileText, Trash2, Upload } from "lucide-react"
import { ErrorState, LoadingState } from "@/components/states"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Spinner } from "@/components/ui/spinner"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { apiErrorMessage, deleteDocument, fetchDocuments, uploadDocument } from "@/lib/api"
import { formatDate } from "@/lib/format"
import { useAuth } from "@/lib/auth"
import { REFRESH_MS } from "@/lib/constants"
import { cn } from "cn"

function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B"
  const units = ["B", "KB", "MB", "GB"]
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  const value = bytes / 1024 ** exponent
  return `${value >= 100 || exponent === 0 ? Math.round(value) : value.toFixed(1)} ${units[exponent]}`
}

/** Knowledge-base document states; unknown values render neutrally. */
function docStatusTone(status: string): string {
  switch (status) {
    case "indexed":
    case "ok":
      return "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-300"
    case "queued":
    case "pending":
      return "border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-900 dark:bg-sky-950 dark:text-sky-300"
    case "failed":
    case "error":
      return "border-red-200 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
    default:
      return "text-muted-foreground"
  }
}

export function DocumentsPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === "admin"
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const documentsQuery = useQuery({
    queryKey: ["documents"],
    queryFn: fetchDocuments,
    refetchInterval: REFRESH_MS,
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadDocument(file),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["documents"] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteDocument(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["documents"] })
    },
  })

  function handleFileSelected(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ""
    if (file !== undefined) {
      uploadMutation.mutate(file)
    }
  }

  const busy = uploadMutation.isPending || deleteMutation.isPending
  const documents = documentsQuery.data ?? []

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-2.5 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-sm font-semibold">Knowledge base</h1>
          <p className="text-xs text-muted-foreground">
            Documents the AI can cite when answering customers
            {isAdmin ? " · admins may upload and delete" : ""}
          </p>
        </div>
        {isAdmin && (
          <>
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              onChange={handleFileSelected}
              aria-label="Upload a knowledge base document"
            />
            <Button size="sm" disabled={busy} onClick={() => fileInputRef.current?.click()}>
              {uploadMutation.isPending ? (
                <>
                  <Spinner className="text-primary-foreground" />
                  Uploading…
                </>
              ) : (
                <>
                  <Upload />
                  Upload
                </>
              )}
            </Button>
          </>
        )}
      </div>

      {(uploadMutation.isError || deleteMutation.isError) && (
        <Alert variant="destructive">
          <AlertDescription>
            {apiErrorMessage(uploadMutation.error ?? deleteMutation.error)}
          </AlertDescription>
        </Alert>
      )}

      {documentsQuery.isError ? (
        <Card>
          <ErrorState
            message={apiErrorMessage(documentsQuery.error)}
            onRetry={() => void documentsQuery.refetch()}
          />
        </Card>
      ) : (
        <Card className="overflow-hidden py-0">
          {documentsQuery.isPending ? (
            <LoadingState rows={5} label="Loading documents…" />
          ) : documents.length === 0 ? (
            <div className="flex flex-col items-center gap-2 px-4 py-12 text-center">
              <FileText className="size-8 text-muted-foreground/50" />
              <p className="text-sm font-medium">No documents yet</p>
              <p className="max-w-sm text-xs text-muted-foreground">
                Seed knowledge is loaded at backend startup; uploaded documents appear here.
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Title</TableHead>
                  <TableHead className="hidden md:table-cell">Type</TableHead>
                  <TableHead className="text-right">Size</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="hidden sm:table-cell">Added</TableHead>
                  {isAdmin && (
                    <TableHead className="w-10">
                      <span className="sr-only">Delete</span>
                    </TableHead>
                  )}
                </TableRow>
              </TableHeader>
              <TableBody>
                {documents.map((document) => (
                  <TableRow key={document.id}>
                    <TableCell className="max-w-64 truncate font-medium" title={document.title}>
                      {document.title}
                      <span className="ml-2 text-[11px] text-muted-foreground">
                        v{document.version}
                      </span>
                    </TableCell>
                    <TableCell
                      className="hidden max-w-40 truncate text-muted-foreground md:table-cell"
                      title={document.mime_type}
                    >
                      {document.mime_type || "—"}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-muted-foreground">
                      {formatBytes(document.size_bytes)}
                    </TableCell>
                    <TableCell>
                      <span
                        className={cn(
                          "inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium",
                          docStatusTone(document.status),
                        )}
                      >
                        {document.status}
                      </span>
                    </TableCell>
                    <TableCell className="hidden text-muted-foreground tabular-nums sm:table-cell">
                      {formatDate(document.created_at)}
                    </TableCell>
                    {isAdmin && (
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          disabled={busy}
                          title="Queue this document for deletion"
                          aria-label={`Delete ${document.title}`}
                          onClick={() => deleteMutation.mutate(document.id)}
                        >
                          <Trash2 className="text-muted-foreground hover:text-destructive" />
                        </Button>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Card>
      )}

      {!documentsQuery.isError && documents.length > 0 && (
        <p className="px-1 text-[11px] text-muted-foreground tabular-nums">
          {documents.length} document{documents.length === 1 ? "" : "s"}
        </p>
      )}
    </div>
  )
}
