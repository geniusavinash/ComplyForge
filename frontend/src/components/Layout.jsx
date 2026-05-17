import { NavLink, Outlet } from 'react-router-dom'
import {
  Activity,
  UploadCloud,
  Table,
  Grid,
  FileText,
  ShieldAlert,
} from 'lucide-react'
import { computeCountdown } from '../lib/enforcement'

function CountdownPill() {
  const { active, days } = computeCountdown()
  if (active) {
    return (
      <span className="inline-flex items-center gap-2 rounded-full bg-risk-prohibited px-4 py-1 text-sm font-semibold text-white">
        ENFORCEMENT ACTIVE
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-border-soft bg-bg-panel px-4 py-1 text-sm font-medium text-accent">
      Aug 2, 2026 — {days} days
    </span>
  )
}

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', Icon: Activity, end: true },
  { to: '/analyze', label: 'New Analysis', Icon: UploadCloud },
  { to: '/inventory', label: 'Inventory', Icon: Table },
  { to: '/heatmap', label: 'Risk Heatmap', Icon: Grid },
  { to: '/docs', label: 'Docs Library', Icon: FileText },
  { to: '/enforcement', label: 'Enforcement Log', Icon: ShieldAlert },
]

function Sidebar() {
  return (
    <aside className="fixed left-0 top-16 bottom-0 w-60 border-r border-border-soft bg-bg-panel">
      <nav className="flex flex-col gap-1 p-4">
        {NAV_ITEMS.map(({ to, label, Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              [
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-accent text-bg-base'
                  : 'text-text-dim hover:text-text-main hover:bg-border-soft/40',
              ].join(' ')
            }
          >
            <Icon size={18} aria-hidden="true" />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}

function TopBar() {
  return (
    <header className="fixed left-0 right-0 top-0 z-10 flex h-16 items-center justify-between border-b border-border-soft bg-bg-panel px-6">
      <div className="flex items-baseline gap-3">
        <span className="text-xl font-bold tracking-tight text-text-main">
          ComplyForge
        </span>
        <span className="italic text-sm text-text-dim">
          EU AI Act Compliance Co-Pilot
        </span>
      </div>
      <CountdownPill />
    </header>
  )
}

export default function Layout() {
  return (
    <div className="min-h-screen bg-bg-base text-text-main">
      <TopBar />
      <Sidebar />
      <main className="ml-60 mt-16 px-6 py-6">
        <div className="mx-auto max-w-screen-2xl space-y-6">
          <div className="rounded-xl border border-border-soft bg-bg-panel p-6">
            <Outlet />
          </div>
        </div>
      </main>
    </div>
  )
}
