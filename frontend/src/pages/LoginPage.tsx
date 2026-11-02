import { useState, type FormEvent } from "react"
import { Navigate, useLocation } from "react-router-dom"
import { useAuth } from "../lib/auth"
import { ApiError } from "../lib/api"
import { Button } from "../components/ui/Button"
import { Input } from "../components/ui/Input"
import { Spinner } from "../components/ui/Spinner"
import { ChatIcon } from "../components/ui/icons"

export function LoginPage() {
  const { status, login } = useAuth()
  const location = useLocation()
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const expired =
    (location.state as { reason?: string } | null)?.reason === "expired"

  if (status === "authed") {
    return <Navigate to="/" replace />
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (username.trim() === "" || password === "" || busy) {
      return
    }
    setBusy(true)
    setError(null)
    try {
      await login(username.trim(), password)
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Wrong username or password")
      } else if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError("Login failed. Please try again.")
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid min-h-svh place-items-center bg-bg p-4">
      <div className="w-full max-w-sm">
        <div className="mb-4 flex items-center justify-center gap-2">
          <span className="grid size-9 place-items-center rounded-lg bg-accent text-accent-fg">
            <ChatIcon className="size-4.5" />
          </span>
          <div className="leading-tight">
            <h1 className="text-base font-semibold">Support Admin</h1>
            <p className="text-xs text-muted-fg">Harbor &amp; Pine customer support</p>
          </div>
        </div>

        <div className="rounded-lg border border-line bg-surface p-4 shadow-sm">
          {expired && (
            <p className="mb-3 rounded-md bg-amber-50 px-2.5 py-2 text-xs text-amber-800 dark:bg-amber-950 dark:text-amber-300">
              Your session expired. Please log in again.
            </p>
          )}
          <p className="mb-3 text-[11px] text-muted-fg">
            Uses the seeded dashboard account, e.g. <span className="font-medium">admin@local</span> with{" "}
            <span className="font-medium">DASHBOARD_PASSWORD</span>.
          </p>
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="username" className="text-xs font-medium text-muted-fg">
                Email or username
              </label>
              <Input
                id="username"
                autoComplete="username"
                autoFocus
                value={username}
                onChange={(event) => setUsername(event.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="password" className="text-xs font-medium text-muted-fg">
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
            {error && <p className="text-xs text-red-500">{error}</p>}
            <Button type="submit" disabled={busy} className="mt-1 w-full">
              {busy && <Spinner className="text-accent-fg" />}
              {busy ? "Logging in…" : "Log in"}
            </Button>
          </form>
        </div>
      </div>
    </div>
  )
}
