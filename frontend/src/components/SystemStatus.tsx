import { useQuery } from "@tanstack/react-query"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/lib/auth"
import { apiErrorMessage, fetchGmailStatus, fetchReadiness, gmailConnectUrl } from "@/lib/api"
import { REFRESH_MS } from "@/lib/constants"
import type { ReadinessComponent, ReadinessStatus } from "@/lib/types"
import { cn } from "cn"
import type { ComponentPropsWithoutRef } from "react"

const COMPONENT_LABELS: Array<{ key: keyof Omit<ReadinessStatus, "status">; label: string }> = [
  { key: "database", label: "Database" },
  { key: "qdrant", label: "Qdrant" },
  { key: "gmail", label: "Gmail" },
]

function Dot({ component }: { component: ReadinessComponent }) {
  const tone =
    component.status === "ok"
      ? "bg-emerald-500"
      : component.status === "error"
        ? "bg-red-500"
        : "bg-muted-foreground/40"
  return <span className={cn("size-2 shrink-0 rounded-full", tone)} aria-hidden="true" />
}

export function SystemStatus({ className }: { className?: string }) {
  const { user } = useAuth()
  const isAdmin = user?.role === "admin"

  const readiness = useQuery({
    queryKey: ["readiness"],
    queryFn: fetchReadiness,
    refetchInterval: REFRESH_MS,
    // 503 with a body is a valid answer here, not a network-level failure.
    retry: false,
  })

  const gmail = useQuery({
    queryKey: ["gmail-status"],
    queryFn: fetchGmailStatus,
    refetchInterval: REFRESH_MS,
  })

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">System status</CardTitle>
        <CardDescription className="text-xs">
          Live backend components — refreshes every {REFRESH_MS / 1000}s
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {readiness.isPending ? (
          <div className="flex flex-col gap-2">
            <Skeleton className="h-5 w-full" />
            <Skeleton className="h-5 w-2/3" />
          </div>
        ) : readiness.isError ? (
          <p className="text-xs text-muted-foreground">{apiErrorMessage(readiness.error)}</p>
        ) : (
          <div className="flex flex-col gap-2">
            {COMPONENT_LABELS.map(({ key, label }) => {
              const component = readiness.data[key]
              return (
                <div key={key} className="flex items-center gap-2 text-xs">
                  <Dot component={component} />
                  <span className="font-medium">{label}</span>
                  <span className="ml-auto truncate text-muted-foreground" title={component.detail ?? undefined}>
                    {component.status}
                    {component.detail ? ` · ${component.detail}` : ""}
                  </span>
                </div>
              )
            })}
          </div>
        )}

        <Separator />

        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium">Gmail account</span>
          {gmail.isPending ? (
            <Skeleton className="h-4 w-32" />
          ) : gmail.isError ? (
            <span className="text-xs text-muted-foreground">{apiErrorMessage(gmail.error)}</span>
          ) :gmail.data.connected ? (
            <span className="text-xs text-emerald-600 dark:text-emerald-400">
              {gmail.data.email ?? "connected"}
            </span>
          ) : (
            <span className="text-xs text-muted-foreground">
              {gmail.data.status ?? "not connected"}
              {gmail.data.last_error ? ` · ${gmail.data.last_error}` : ""}
            </span>
          )}
          {isAdmin && (
            <ConnectButton className="ml-auto" connected={gmail.data?.connected === true} />
          )}
        </div>
      </CardContent>
    </Card>
  )
}

/** Full-page navigation to the backend OAuth redirect. */
function ConnectButton({
  connected,
  className,
  ...props
}: { connected: boolean } & ComponentPropsWithoutRef<typeof Button>) {
  return (
    <Button asChild size="sm" variant={connected ? "outline" : "default"} className={className} {...props}>
      <a href={gmailConnectUrl()}>{connected ? "Reconnect" : "Connect Gmail"}</a>
    </Button>
  )
}
