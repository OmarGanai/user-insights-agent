export function isoNow(): string {
  return new Date().toISOString()
}

export function toRelativeTime(iso: string | null): string {
  if (!iso) return "Never"

  const now = Date.now()
  const then = Date.parse(iso)
  if (Number.isNaN(then)) return "Unknown"

  const diffMs = Math.max(0, now - then)
  const diffMinutes = Math.floor(diffMs / 60000)

  if (diffMinutes < 1) return "Just now"
  if (diffMinutes < 60) return `${diffMinutes} min ago`

  const diffHours = Math.floor(diffMinutes / 60)
  if (diffHours < 24) return `${diffHours} hr ago`

  const diffDays = Math.floor(diffHours / 24)
  return `${diffDays} day${diffDays === 1 ? "" : "s"} ago`
}

export function startOfDayIso(daysAgo = 0): string {
  const day = new Date()
  day.setUTCDate(day.getUTCDate() - daysAgo)
  day.setUTCHours(0, 0, 0, 0)
  return day.toISOString()
}
