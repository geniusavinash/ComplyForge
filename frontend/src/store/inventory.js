import { create } from 'zustand'
import { getEnforcementEvents } from '../api/client'

const POLL_INTERVAL_MS = 2000
const MAX_EVENTS = 500

let pollHandle = null

export const useInventory = create((set, get) => ({
  // state
  reports: {}, // keyed by agent.name -> ComplianceReport
  events: [], // capped to MAX_EVENTS, newest first
  lastUpdated: null,

  // actions
  addReport: (report) => {
    if (!report || !report.agent || !report.agent.name) return
    set((state) => ({
      reports: { ...state.reports, [report.agent.name]: report },
      lastUpdated: new Date().toISOString(),
    }))
  },

  upsertReport: (report) => {
    if (!report || !report.agent || !report.agent.name) return
    set((state) => ({
      reports: { ...state.reports, [report.agent.name]: report },
      lastUpdated: new Date().toISOString(),
    }))
  },

  setEvents: (events) => {
    const list = Array.isArray(events) ? events.slice(0, MAX_EVENTS) : []
    // Newest-first ordering for the live feed.
    list.sort((a, b) => {
      const ta = new Date(a?.timestamp || 0).getTime()
      const tb = new Date(b?.timestamp || 0).getTime()
      return tb - ta
    })
    set({ events: list, lastUpdated: new Date().toISOString() })
  },

  addEvent: (event) => {
    if (!event) return
    set((state) => ({
      events: [event, ...state.events].slice(0, MAX_EVENTS),
      lastUpdated: new Date().toISOString(),
    }))
  },

  // polling — idempotent
  startPolling: () => {
    if (pollHandle !== null) return
    const tick = async () => {
      try {
        const events = await getEnforcementEvents(MAX_EVENTS)
        get().setEvents(events)
      } catch {
        // swallow polling errors so we don't spam the console; backend may be down
      }
    }
    // fire immediately, then on interval
    tick()
    pollHandle = setInterval(tick, POLL_INTERVAL_MS)
  },

  stopPolling: () => {
    if (pollHandle !== null) {
      clearInterval(pollHandle)
      pollHandle = null
    }
  },
}))

// ---------------------------------------------------------------------------
// Selectors
// ---------------------------------------------------------------------------
export const selectByTier = (tier) => (state) =>
  Object.values(state.reports).filter(
    (r) => r?.classification?.tier === tier,
  )

export const selectByName = (name) => (state) => state.reports[name] || null

const ATTACK_ACTIONS = new Set(['DENY', 'QUARANTINE'])
const REVIEW_ACTIONS = new Set(['HUMAN_REVIEW'])
const RATE_ACTIONS = new Set(['RATE_LIMIT'])

/**
 * Roll-up stats for the dashboard / enforcement KPI strips.
 *
 * Windows:
 *   - attacksBlocked / humanReviewQueued / rateLimited: events whose timestamp
 *     is within the last 24 hours.
 *   - eventsToday: events since local-midnight today.
 *   - totalEvents: raw count of events in state.
 *   - agentsAnalyzed: number of distinct ComplianceReports in the store.
 *   - highOrProhibitedCount: reports classified high_risk or prohibited.
 */
export function deriveStats(state) {
  const now = Date.now()
  const dayAgo = now - 24 * 60 * 60 * 1000
  const startOfDay = new Date()
  startOfDay.setHours(0, 0, 0, 0)
  const startOfDayMs = startOfDay.getTime()

  let attacksBlocked = 0
  let humanReviewQueued = 0
  let rateLimited = 0
  let eventsToday = 0

  for (const ev of state.events || []) {
    const t = new Date(ev?.timestamp || 0).getTime()
    if (t >= startOfDayMs) eventsToday += 1
    if (t < dayAgo) continue
    const a = ev?.action
    if (ATTACK_ACTIONS.has(a)) attacksBlocked += 1
    else if (REVIEW_ACTIONS.has(a)) humanReviewQueued += 1
    else if (RATE_ACTIONS.has(a)) rateLimited += 1
  }

  const reports = Object.values(state.reports || {})
  const agentsAnalyzed = reports.length
  const highOrProhibitedCount = reports.filter((r) => {
    const t = r?.classification?.tier
    return t === 'high_risk' || t === 'prohibited'
  }).length

  // Planner + Critic roll-ups (optional fields on ComplianceReport).
  const reportsWithCritique = reports.filter((r) => r?.critique != null)
  const criticDissents = reportsWithCritique.filter(
    (r) => r.critique?.agreed === false,
  ).length
  const plansExecuted = reports.filter((r) => r?.plan != null).length

  return {
    agentsAnalyzed,
    highOrProhibitedCount,
    eventsToday,
    attacksBlocked,
    humanReviewQueued,
    rateLimited,
    totalEvents: (state.events || []).length,
    criticDissents,
    plansExecuted,
    reportsWithCritiqueCount: reportsWithCritique.length,
  }
}
