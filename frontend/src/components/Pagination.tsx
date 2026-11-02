import { Button } from "@/components/ui/button"

export interface PaginationProps {
  page: number
  pageCount: number
  onPageChange: (page: number) => void
}

export function Pagination({ page, pageCount, onPageChange }: PaginationProps) {
  if (pageCount <= 1) {
    return null
  }
  return (
    <div className="flex items-center justify-between px-3 py-2">
      <p className="text-xs text-muted-foreground tabular-nums">
        Page {page} of {pageCount}
      </p>
      <div className="flex gap-1.5">
        <Button
          variant="outline"
          size="sm"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          Prev
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={page >= pageCount}
          onClick={() => onPageChange(page + 1)}
        >
          Next
        </Button>
      </div>
    </div>
  )
}
