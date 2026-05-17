// Shared EU AI Act high-risk enforcement countdown (Aug 2, 2026).
export const ENFORCEMENT_DATE = new Date('2026-08-02T00:00:00Z')
export const MS_PER_DAY = 86400000

export function computeCountdown(now = new Date()) {
  const diffMs = ENFORCEMENT_DATE.getTime() - now.getTime()
  if (diffMs <= 0) return { active: true, days: 0 }
  return { active: false, days: Math.ceil(diffMs / MS_PER_DAY) }
}
