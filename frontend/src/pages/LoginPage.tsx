import { useState, type FormEvent } from "react"
import { Navigate, useLocation } from "react-router-dom"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Spinner } from "@/components/ui/spinner"
import { MessageSquare } from "lucide-react"
import { useAuth } from "@/lib/auth"
import { apiErrorMessage, isNotImplemented } from "@/lib/api"

export function LoginPage() {
  const { status, login } = useAuth()
  const location = useLocation()
  const [identifier, setIdentifier] = useState("")
  const [password, setPassword] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const expired = (location.state as { reason?: string } | null)?.reason === "expired"

  if (status === "authed") {
    return <Navigate to="/" replace />
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (identifier.trim() === "" || password === "" || busy) {
      return
    }
    setBusy(true)
    setError(null)
    try {
      await login(identifier.trim(), password)
    } catch (err) {
      if (isNotImplemented(err)) {
        setError("Login is not wired up on the backend yet.")
      } else {
        setError(apiErrorMessage(err))
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid min-h-svh place-items-center p-4">
      <div className="w-full max-w-sm">
        <div className="mb-4 flex items-center justify-center gap-2">
          <span className="grid size-9 place-items-center rounded-lg bg-primary text-primary-foreground">
            <MessageSquare className="size-4.5" />
          </span>
          <div className="leading-tight">
            <h1 className="text-base font-semibold">Support Admin</h1>
            <p className="text-xs text-muted-foreground">Harbor &amp; Pine customer support</p>
          </div>
        </div>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Log in</CardTitle>
            <CardDescription className="text-xs">
              Uses the seeded dashboard account, e.g. <span className="font-medium">admin@local</span>{" "}
              with <span className="font-medium">DASHBOARD_PASSWORD</span>.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {expired && (
              <p className="mb-3 rounded-md bg-amber-50 px-2.5 py-2 text-xs text-amber-800 dark:bg-amber-950 dark:text-amber-300">
                Your session expired. Please log in again.
              </p>
            )}
            <form onSubmit={handleSubmit} className="flex flex-col gap-3">
              <div className="flex flex-col gap-1.5">
                <label htmlFor="identifier" className="text-xs font-medium text-muted-foreground">
                  Email or username
                </label>
                <Input
                  id="identifier"
                  autoComplete="username"
                  autoFocus
                  value={identifier}
                  onChange={(event) => setIdentifier(event.target.value)}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="password" className="text-xs font-medium text-muted-foreground">
                  Password
                </label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </div>
              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
              <Button type="submit" disabled={busy} className="mt-1 w-full">
                {busy && <Spinner className="text-primary-foreground" />}
                {busy ? "Logging in…" : "Log in"}
              </Button>
            </form>
          </CardContent>
          <CardFooter className="justify-center text-[11px] text-muted-foreground">
            The session is a cookie set by the API — nothing is stored in the browser.
          </CardFooter>
        </Card>
      </div>
    </div>
  )
}
