import { formatDate } from "./format"

/** Compact relative time for timestamps close to now (e.g. "3m ago"). */
export function formatDistanceToNowStrict(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  const diffMs = Date.now() - date.getTime()
  const seconds = Math.round(Math.abs(diffMs) / 1000)

  let text: string
  if (seconds < 60) text = `${seconds}s`
  else if (seconds < 3600) text = `${Math.round(seconds / 60)}m`
  else if (seconds < 86_400) text = `${Math.round(seconds / 3600)}h`
  else if (seconds < 2_592_000) text = `${Math.round(seconds / 86_400)}d`
  else text = formatDate(value)

  return diffMs >= 0 ? `${text} ago` : `in ${text}`
}
