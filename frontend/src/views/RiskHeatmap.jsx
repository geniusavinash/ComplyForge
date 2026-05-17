import { Link } from 'react-router-dom'
import { useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useInventory } from '../store/inventory'
import { TIER_HEX, BORDER_HEX, TEXT_DIM_HEX, TEXT_MAIN_HEX, PANEL_HEX } from '../lib/palette'

const TIERS = [
  { key: 'prohibited', label: 'Prohibited' },
  { key: 'high_risk', label: 'High risk' },
  { key: 'limited_risk', label: 'Limited risk' },
  { key: 'minimal_risk', label: 'Minimal risk' },
]

// JIT-friendly intensity classes — every class string is literal so the
// Tailwind scanner picks them up at build time.
const INTENSITY = {
  prohibited: ['bg-bg-panel', 'bg-risk-prohibited/30', 'bg-risk-prohibited/60', 'bg-risk-prohibited/90'],
  high_risk: ['bg-bg-panel', 'bg-risk-high/30', 'bg-risk-high/60', 'bg-risk-high/90'],
  limited_risk: ['bg-bg-panel', 'bg-risk-limited/30', 'bg-risk-limited/60', 'bg-risk-limited/90'],
  minimal_risk: ['bg-bg-panel', 'bg-risk-minimal/30', 'bg-risk-minimal/60', 'bg-risk-minimal/90'],
}

function intensity(count, tier) {
  const arr = INTENSITY[tier] || INTENSITY.high_risk
  if (count <= 0) return arr[0]
  if (count === 1) return arr[1]
  if (count === 2) return arr[2]
  return arr[3]
}

export default function RiskHeatmap() {
  const reports = useInventory((s) => s.reports)
  const list = useMemo(() => Object.values(reports), [reports])
  const [tierFilter, setTierFilter] = useState(new Set()) // empty = all

  const filtered = useMemo(() => {
    if (tierFilter.size === 0) return list
    return list.filter((r) => tierFilter.has(r.classification?.tier))
  }, [list, tierFilter])

  const domains = useMemo(() => {
    const s = new Set()
    for (const r of filtered) if (r.agent?.domain) s.add(r.agent.domain)
    return [...s].sort()
  }, [filtered])

  const grid = useMemo(() => {
    const map = {}
    for (const d of domains) {
      map[d] = { prohibited: 0, high_risk: 0, limited_risk: 0, minimal_risk: 0 }
    }
    for (const r of filtered) {
      const d = r.agent?.domain
      const t = r.classification?.tier
      if (!d || !map[d] || !t || !(t in map[d])) continue
      map[d][t] += 1
    }
    return map
  }, [filtered, domains])

  const articleStats = useMemo(() => {
    const counts = {} // article -> { count, tiers: {tier: count} }
    for (const r of filtered) {
      const tier = r.classification?.tier || 'unknown'
      for (const a of r.classification?.triggered_articles || []) {
        if (!counts[a]) counts[a] = { count: 0, tiers: {} }
        counts[a].count += 1
        counts[a].tiers[tier] = (counts[a].tiers[tier] || 0) + 1
      }
    }
    const rows = Object.entries(counts).map(([article, info]) => {
      let modeTier = 'unknown'
      let best = -1
      for (const [tier, c] of Object.entries(info.tiers)) {
        if (c > best) {
          best = c
          modeTier = tier
        }
      }
      return { article, count: info.count, tier: modeTier }
    })
    rows.sort((a, b) => b.count - a.count)
    return rows.slice(0, 10)
  }, [filtered])

  const toggleTier = (k) => {
    setTierFilter((prev) => {
      const next = new Set(prev)
      if (next.has(k)) next.delete(k)
      else next.add(k)
      return next
    })
  }

  if (list.length === 0) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold text-text-main">Risk Heatmap</h1>
        <div className="rounded-xl border border-dashed border-border-soft bg-bg-panel p-10 text-center">
          <p className="text-sm text-text-dim">
            No analyses yet. Run an analysis to populate the heatmap.
          </p>
          <Link
            to="/analyze"
            className="mt-4 inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-bg-base hover:bg-accent/90"
          >
            New Analysis
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-semibold text-text-main">Risk Heatmap</h1>
        <div className="flex flex-wrap gap-2">
          <FilterChip
            active={tierFilter.size === 0}
            onClick={() => setTierFilter(new Set())}
          >
            All tiers
          </FilterChip>
          {TIERS.map((t) => (
            <FilterChip
              key={t.key}
              active={tierFilter.has(t.key)}
              onClick={() => toggleTier(t.key)}
            >
              {t.label}
            </FilterChip>
          ))}
        </div>
      </header>

      <section className="rounded-xl border border-border-soft bg-bg-panel p-5">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-text-dim">
          Domains × tiers
        </h2>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full border-separate border-spacing-1 text-sm">
            <thead>
              <tr>
                <th className="w-48 px-2 py-1 text-left text-xs uppercase tracking-wide text-text-dim">
                  Domain
                </th>
                {TIERS.map((t) => (
                  <th
                    key={t.key}
                    className="px-2 py-1 text-center text-xs uppercase tracking-wide text-text-dim"
                  >
                    {t.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {domains.map((d) => (
                <tr key={d}>
                  <th
                    scope="row"
                    className="w-48 px-2 py-1 text-left font-medium text-text-main"
                  >
                    {d}
                  </th>
                  {TIERS.map((t) => {
                    const count = grid[d]?.[t.key] || 0
                    return (
                      <td key={t.key} className="px-1 py-1">
                        <div
                          className={[
                            'flex h-12 items-center justify-center rounded-md text-sm font-semibold transition-colors',
                            intensity(count, t.key),
                            count > 0 ? 'text-white' : 'text-text-dim/50',
                          ].join(' ')}
                          title={`${d} · ${t.label}: ${count}`}
                        >
                          {count > 0 ? count : '·'}
                        </div>
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-xl border border-border-soft bg-bg-panel p-5">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-text-dim">
          Top triggered articles
        </h2>
        {articleStats.length === 0 ? (
          <p className="mt-4 text-sm text-text-dim">
            No articles triggered yet.
          </p>
        ) : (
          <div className="mt-4 h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={articleStats}
                layout="vertical"
                margin={{ top: 8, right: 16, left: 8, bottom: 8 }}
              >
                <CartesianGrid stroke={BORDER_HEX} strokeDasharray="3 3" />
                <XAxis
                  type="number"
                  stroke={TEXT_DIM_HEX}
                  fontSize={11}
                  allowDecimals={false}
                />
                <YAxis
                  dataKey="article"
                  type="category"
                  stroke={TEXT_DIM_HEX}
                  fontSize={11}
                  width={140}
                />
                <Tooltip
                  contentStyle={{
                    background: PANEL_HEX,
                    border: `1px solid ${BORDER_HEX}`,
                    color: TEXT_MAIN_HEX,
                    fontSize: 12,
                  }}
                  cursor={{ fill: 'rgba(245,158,11,0.08)' }}
                />
                <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                  {articleStats.map((row, i) => (
                    <Cell
                      key={`cell-${i}`}
                      fill={TIER_HEX[row.tier] || TIER_HEX.unknown}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>
    </div>
  )
}

function FilterChip({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        'rounded-full border px-3 py-1 text-xs transition-colors',
        active
          ? 'border-accent bg-accent text-bg-base'
          : 'border-border-soft text-text-dim hover:text-text-main',
      ].join(' ')}
    >
      {children}
    </button>
  )
}
