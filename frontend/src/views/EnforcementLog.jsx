import { useEffect, useMemo, useRef, useState } from 'react'
import { ChevronDown, ChevronRight, Pause, Play } from 'lucide-react'
import ActionChip from '../components/ActionChip'
import { useInventory, deriveStats } from '../store/inventory'
import { clockTime, truncate } from '../lib/format'

function StatCard({ label, value }) {
  const [pulse, setPulse] = useState(false)
  const prev = useRef(value)
  useEffect(() => {
    if (value !== prev.current && value > prev.current) {
      setPulse(true)
      const id = setTimeout(() => setPulse(false), 600)
      prev.current = value
      return () => clearTimeout(id)
    }
    prev.current = value
  }, [value])

  return (
    <div className="rounded-xl border border-border-soft bg-bg-panel p-4">
      <div className="text-xs uppercase tracking-wide text-text-dim">
        {label}
      </div>
      <div
        className={[
          'mt-2 text-3xl font-bold tabular-nums text-text-main transition-transform',
          pulse ? 'animate-stat-pulse' : '',
        ].join(' ')}
      >
        {value}
      </div>
    </div>
  )
}

export default function EnforcementLog() {
  const events = useInventory((s) => s.events)
  const reports = useInventory((s) => s.reports)
  const stats = deriveStats({ reports, events })

  const [autoRefresh, setAutoRefresh] = useState(true)
  const [expanded, setExpanded] = useState(() => new Set())

  const toggleAuto = () => {
    const store = useInventory.getState()
    if (autoRefresh) {
      store.stopPolling()
      setAutoRefresh(false)
    } else {
      store.startPolling()
      setAutoRefresh(true)
    }
  }

  const toggleRow = (key) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const list = useMemo(() => events || [], [events])

  return (
    <div className="space-y-5">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-text-main">
            Enforcement Log
          </h1>
          <p className="text-sm text-text-dim">
            Live events relayed from Veea Lobster Trap via webhook_bridge.py.
          </p>
        </div>
        <button
          type="button"
          onClick={toggleAuto}
          className={[
            'inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-xs transition-colors',
            autoRefresh
              ? 'border-accent text-accent hover:bg-accent/10'
              : 'border-border-soft text-text-dim hover:text-text-main',
          ].join(' ')}
        >
          {autoRefresh ? <Pause size={12} /> : <Play size={12} />}
          Auto-refresh {autoRefresh ? 'on' : 'off'}
        </button>
      </header>

      <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="Attacks blocked (24h)" value={stats.attacksBlocked} />
        <StatCard label="Human review (24h)" value={stats.humanReviewQueued} />
        <StatCard label="Rate limited (24h)" value={stats.rateLimited} />
        <StatCard label="Total events" value={stats.totalEvents} />
      </section>

      {list.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border-soft bg-bg-panel p-10 text-center">
          <p className="animate-pulse text-sm text-text-dim">
            Waiting for events…
          </p>
          <p className="mt-2 text-xs text-text-dim">
            Start <span className="font-mono">webhook_bridge.py</span> against a
            running Lobster Trap proxy to populate this feed.
          </p>
        </div>
      ) : (
        <ul className="divide-y divide-border-soft rounded-xl border border-border-soft bg-bg-panel">
          {list.map((e, i) => {
            const key = `${e.timestamp}-${i}`
            const open = expanded.has(key)
            return (
              <li key={key} className="px-4 py-3">
                <button
                  type="button"
                  onClick={() => toggleRow(key)}
                  className="flex w-full items-start gap-3 text-left"
                >
                  <span className="mt-0.5 text-text-dim">
                    {open ? (
                      <ChevronDown size={14} />
                    ) : (
                      <ChevronRight size={14} />
                    )}
                  </span>
                  <span className="w-20 shrink-0 font-mono text-xs text-text-dim">
                    {clockTime(e.timestamp)}
                  </span>
                  <span className="shrink-0">
                    <ActionChip action={e.action} />
                  </span>
                  <span className="w-40 shrink-0 truncate text-sm text-text-main">
                    {e.agent_name || '—'}
                  </span>
                  <span className="w-56 shrink-0 truncate font-mono text-xs text-text-dim">
                    {e.rule_triggered || '—'}
                  </span>
                  <span className="flex-1 truncate text-xs text-text-dim">
                    {truncate(e.request_snippet, 80)}
                  </span>
                </button>
                {open && (
                  <pre className="mt-3 max-h-64 overflow-auto rounded bg-bg-base p-3 font-mono text-[11px] leading-relaxed text-text-main">
                    {JSON.stringify(e, null, 2)}
                  </pre>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
