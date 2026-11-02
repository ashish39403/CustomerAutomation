import type { ReactNode } from "react"
import { NavLink } from "react-router-dom"
import { useAuth } from "../lib/auth"
import { cn } from "../lib/cn"
import { useTheme } from "../lib/theme"
import { Button } from "./ui/Button"
import { ChatIcon, MoonIcon, SunIcon } from "./ui/icons"

function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  return (
    <Button
      variant="ghost"
      size="sm"
      className="size-8 p-0 hidden sm:inline-flex"
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      title="Toggle dark mode"
      aria-label="Toggle dark mode"
    >
      {theme === "dark" ? <SunIcon /> : <MoonIcon />}
    </Button>
  )
}

function UserChip() {
  const { user } = useAuth()
  if (user === null) {
    return null
  }
  return (
    <span className="hidden items-center gap-1.5 border-r border-line pr-2 lg:flex">
      <span className="max-w-44 truncate text-xs text-muted-fg" title={user.email}>
        {user.display_name !== "" ? user.display_name : user.email}
      </span>
      <span className="rounded-full bg-soft px-2 py-0.5 text-[11px] font-medium text-muted-fg">
        {user.role}
      </span>
    </span>
  )
}

export function Layout({ children }: { children: ReactNode }) {
  const { logout } = useAuth()

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    cn(
      "rounded-md px-2.5 py-1.5 text-sm font-medium transition-colors whitespace-nowrap",
      isActive ? "bg-soft text-fg" : "text-muted-fg hover:text-fg",
    )

  return (
    <div className="min-h-svh">
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex max-w-5xl flex-col gap-2 px-4 py-2.5 sm:flex-row sm:items-center sm:justify-between sm:gap-4 sm:px-6">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="grid size-7 shrink-0 place-items-center rounded-md bg-accent text-accent-fg">
                <ChatIcon className="size-4" />
              </span>
              <div className="flex flex-col leading-tight">
                <span className="text-sm font-semibold">Support Admin</span>
                <span className="hidden text-[11px] text-muted-fg sm:block">
                  Harbor &amp; Pine customer support
                </span>
              </div>
            </div>
            <div className="flex items-center gap-1.5 sm:hidden">
              <ThemeToggle />
              <Button variant="outline" size="sm" onClick={logout}>
                Log out
              </Button>
            </div>
          </div>
          <div className="flex items-center justify-between gap-2 sm:justify-end">
            <nav className="flex min-w-0 flex-1 items-center gap-0.5 overflow-x-auto sm:flex-none">
              <NavLink to="/" end className={linkClass}>
                Overview
              </NavLink>
              <NavLink to="/tickets" className={linkClass}>
                Tickets
              </NavLink>
            </nav>
            <div className="hidden items-center gap-1.5 sm:flex">
              <UserChip />
              <ThemeToggle />
              <Button variant="outline" size="sm" onClick={logout}>
                Log out
              </Button>
            </div>
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-5xl px-4 py-5 sm:px-6 sm:py-6">{children}</main>
    </div>
  )
}
