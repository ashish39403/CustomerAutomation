import { Link } from "react-router-dom"

export function NotFoundPage() {
  return (
    <div className="grid min-h-svh place-items-center p-4">
      <div className="flex flex-col items-center gap-3 text-center">
        <h1 className="text-base font-semibold">Page not found</h1>
        <p className="text-sm text-muted-fg">The page you are looking for does not exist.</p>
        <Link
          to="/"
          className="inline-flex h-9 items-center justify-center rounded-md border border-line bg-surface px-3 text-sm font-medium text-fg transition-colors hover:bg-soft"
        >
          Go to overview
        </Link>
      </div>
    </div>
  )
}
