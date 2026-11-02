import { useQueryClient } from "@tanstack/react-query"
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react"
import { Navigate } from "react-router-dom"
import { apiLogout, fetchMe, login as loginApi, setUnauthorizedHandler } from "./api"
import type { UserSummary } from "./types"
import { Spinner } from "../components/ui/Spinner"

export type AuthStatus = "checking" | "authed" | "guest"

interface AuthContextValue {
  status: AuthStatus
  user: UserSummary | null
  login: (identifier: string, password: string) => Promise<UserSummary | null>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("checking")
  const [user, setUser] = useState<UserSummary | null>(null)
  const queryClient = useQueryClient()

  // Probe the API once on load. /auth/me is cheap and answers 401 without
  // a session, which flips us to the login page.
  useEffect(() => {
    let alive = true
    fetchMe()
      .then((me) => {
        if (!alive) return
        setUser(me)
        setStatus("authed")
      })
      .catch(() => {
        if (!alive) return
        setUser(null)
        setStatus("guest")
      })
    return () => {
      alive = false
    }
  }, [])

  // The API client reports 401s (expired session) here.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      queryClient.clear()
      setUser(null)
      setStatus("guest")
    })
    return () => {
      setUnauthorizedHandler(null)
    }
  }, [queryClient])

  const login = useCallback(
    async (identifier: string, password: string) => {
      const result = await loginApi(identifier, password)
      queryClient.clear()
      setUser(result?.user ?? null)
      setStatus("authed")
      return result?.user ?? null
    },
    [queryClient],
  )

  const logout = useCallback(() => {
    // Best effort: clear the server session, then drop local state even if
    // the call fails. Also removes any user from the session.
    void apiLogout().catch(() => undefined)
    queryClient.clear()
    setUser(null)
    setStatus("guest")
  }, [queryClient])

  const value = useMemo(
    () => ({ status, user, login, logout }),
    [status, user, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (context === null) {
    throw new Error("useAuth must be used inside AuthProvider")
  }
  return context
}

export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth()

  if (status === "checking") {
    return (
      <div className="grid min-h-svh place-items-center">
        <Spinner className="size-6" />
      </div>
    )
  }
  if (status === "guest") {
    return <Navigate to="/login" replace state={{ reason: "expired" }} />
  }
  return <>{children}</>
}
