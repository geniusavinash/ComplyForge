import { Link, useNavigate } from 'react-router-dom'
import {
  ArrowRight,
  Brain,
  GitBranch,
  Hourglass,
  ShieldAlert,
  ShieldCheck,
  Users,
} from 'lucide-react'
import RiskBadge from '../components/RiskBadge'
import ActionChip from '../components/ActionChip'
import { useInventory, deriveStats } from '../store/inventory'
import { computeCountdown } from '../lib/enforcement'
import { relativeTime } from '../lib/format'

function StatCard({ label, value, Icon, accent = false }) {
  return (
    <div
      className={[
        'rounded-xl border border-border-soft bg-bg-panel p-5',
        accent ? 'ring-1 ring-accent/30' : '',
      ].join(' ')}
    >
      <div className="flex items-center justify-between text-text-dim">
        <span className="text-xs uppercase tracking-wide">{label}</span>
        {Icon && <Icon size={16} aria-hidden="true" />}
      </div>
      <div className="mt-2 text-3xl font-bold text-text-main tabular-nums">
        {value}
      </div>
    </div>
  )
}

function CountdownCard() {
  const { active, days } = computeCountdown()
  if (active) {
    return (
      <div className="rounded-xl border border-risk-prohibited/60 bg-risk-prohibited/15 p-6">
        <div className="text-xs uppercase tracking-wide text-risk-prohibited">
          EU AI Act high-risk obligations
        </div>
        <div className="mt-2 text-3xl font-bold text-risk-prohibited">
          ENFORCEMENT ACTIVE
        </div>
        <div className="mt-1 text-sm text-text-dim">
          High-risk obligations are now legally binding under Articles 6, 9, 11,
          14, 27, and 72.
        </div>
      </div>
    )
  }
  return (
    <div className="rounded-xl border border-border-soft bg-bg-panel p-6">
      <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-text-dim">
        <Hourglass size={14} /> Days until high-risk enforcement
      </div>
      <div className="mt-2 flex items-baseline gap-3">
        <span className="text-5xl font-bold text-accent tabular-nums">
          {days}
        </span>
        <span className="text-sm text-text-dim">to Aug 2, 2026</span>
      </div>
      <div className="mt-1 text-sm text-text-dim">
        Article 6 + Annex III obligations become enforceable across the EU.
      </div>
    </div>
  )
}

export default function Dashboard() {
  const reports = useInventory((s) => s.reports)
  const events = useInventory((s) => s.events)
  const stats = deriveStats({ reports, events })
  const navigate = useNavigate()

  const reportList = Object.values(reports)
  const recentReports = [...reportList]
    .sort((a, b) => {
      const ta = new Date(a?.technical_file?.generated_at || 0).getTime()
      const tb = new Date(b?.technical_file?.generated_at || 0).getTime()
      return tb - ta
    })
    .slice(0, 5)

  const recentBlocks = (events || [])
    .filter((e) => e?.action === 'DENY' || e?.action === 'HUMAN_REVIEW')
    .slice(0, 5)

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-text-main">Dashboard</h1>
        <p className="text-sm text-text-dim">
          Live overview of analysed agents, enforcement traffic, and EU AI Act
          countdown.
        </p>
      </header>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <StatCard
          label="Agents analysed"
          value={stats.agentsAnalyzed}
          Icon={Users}
        />
        <StatCard
          label="High-risk + prohibited"
          value={stats.highOrProhibitedCount}
          Icon={ShieldAlert}
          accent={stats.highOrProhibitedCount > 0}
        />
        <StatCard
          label="Enforcement events today"
          value={stats.eventsToday}
          Icon={ShieldCheck}
        />
      </section>

      {(stats.reportsWithCritiqueCount > 0 || stats.plansExecuted > 0) && (
        <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {stats.reportsWithCritiqueCount > 0 && (
            <StatCard
              label="Critic dissents"
              value={stats.criticDissents}
              Icon={Brain}
              accent={stats.criticDissents > 0}
            />
          )}
          {stats.plansExecuted > 0 && (
            <StatCard
              label="Plans executed"
              value={stats.plansExecuted}
              Icon={GitBranch}
            />
          )}
        </section>
      )}

      <CountdownCard />

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-border-soft bg-bg-panel p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-text-dim">
              Recent analyses
            </h2>
            <Link
              to="/inventory"
              className="text-xs text-accent hover:underline"
            >
              All analyses →
            </Link>
          </div>
          {recentReports.length === 0 ? (
            <EmptyHint to="/analyze" cta="Run your first analysis" />
          ) : (
            <ul className="divide-y divide-border-soft">
              {recentReports.map((r) => (
                <li
                  key={r.agent.name}
                  className="flex cursor-pointer items-center justify-between py-3 hover:bg-border-soft/40"
                  onClick={() =>
                    navigate('/inventory', {
                      state: { focusName: r.agent.name },
                    })
                  }
                >
                  <div className="min-w-0">
                    <div className="font-medium text-text-main">
                      {r.agent.name}
                    </div>
                    <div className="truncate text-xs text-text-dim">
                      {r.agent.domain} ·{' '}
                      {relativeTime(r.technical_file?.generated_at)}
                    </div>
                  </div>
                  <RiskBadge tier={r.classification?.tier} size="sm" />
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-xl border border-border-soft bg-bg-panel p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-text-dim">
              Recent blocks
            </h2>
            <Link
              to="/enforcement"
              className="text-xs text-accent hover:underline"
            >
              Full log →
            </Link>
          </div>
          {recentBlocks.length === 0 ? (
            <p className="py-6 text-sm text-text-dim">
              No DENY or HUMAN_REVIEW events yet. Run Lobster Trap with
              webhook_bridge.py to populate this feed.
            </p>
          ) : (
            <ul className="divide-y divide-border-soft">
              {recentBlocks.map((e, i) => (
                <li
                  key={`${e.timestamp}-${i}`}
                  className="flex items-center gap-3 py-3"
                >
                  <ActionChip action={e.action} />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm text-text-main">
                      {e.agent_name}{' '}
                      <span className="text-text-dim">·</span>{' '}
                      {e.rule_triggered}
                    </div>
                    <div className="text-xs text-text-dim">
                      {relativeTime(e.timestamp)}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      <section>
        <Link
          to="/analyze"
          className="inline-flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-bg-base hover:bg-accent/90"
        >
          Run new analysis <ArrowRight size={16} />
        </Link>
      </section>
    </div>
  )
}

function EmptyHint({ to, cta }) {
  return (
    <div className="rounded-lg border border-dashed border-border-soft p-6 text-center">
      <p className="text-sm text-text-dim">
        No analyses yet. Start with a sample agent.
      </p>
      <Link
        to={to}
        className="mt-3 inline-flex items-center gap-2 rounded-md bg-accent px-3 py-1.5 text-xs font-semibold text-bg-base hover:bg-accent/90"
      >
        {cta}
      </Link>
    </div>
  )
}
