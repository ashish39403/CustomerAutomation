import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"

export function NotFoundPage() {
  return (
    <div className="grid min-h-svh place-items-center p-4">
      <div className="flex flex-col items-center gap-3 text-center">
        <h1 className="text-base font-semibold">Page not found</h1>
        <p className="text-sm text-muted-foreground">The page you are looking for does not exist.</p>
        <Button asChild variant="outline" size="sm">
          <Link to="/">Go to overview</Link>
        </Button>
      </div>
    </div>
  )
}
