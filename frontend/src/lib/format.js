import { formatDistanceToNow, parseISO, isValid } from 'date-fns'

export function relativeTime(iso) {
  if (!iso) return '—'
  try {
    const d = typeof iso === 'string' ? parseISO(iso) : iso
    if (!isValid(d)) return '—'
    return formatDistanceToNow(d, { addSuffix: true })
  } catch {
    return '—'
  }
}

export function basename(p) {
  if (!p) return ''
  const s = String(p).replace(/\\/g, '/')
  const i = s.lastIndexOf('/')
  return i === -1 ? s : s.slice(i + 1)
}

export function clockTime(iso) {
  if (!iso) return '—'
  try {
    const d = typeof iso === 'string' ? parseISO(iso) : iso
    if (!isValid(d)) return '—'
    return d.toLocaleTimeString('en-US', { hour12: false })
  } catch {
    return '—'
  }
}

export function truncate(s, n = 80) {
  if (!s) return ''
  return s.length <= n ? s : s.slice(0, n - 1) + '\u2026'
}
