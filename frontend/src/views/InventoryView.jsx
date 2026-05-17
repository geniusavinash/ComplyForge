import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  ClipboardCopy,
  ExternalLink,
  Loader2,
  RotateCw,
  Search,
  X,
} from 'lucide-react'
import RiskBadge from '../components/RiskBadge'
import { useInventory } from '../store/inventory'
import { analyze, getPdfUrl } from '../api/client'
import { toast } from '../store/toasts'
import { basename, relativeTime } from '../lib/format'

const TIERS = [
  { key: 'prohibited', label: 'Prohibited' },
  { key: 'high_risk', label: 'High risk' },
  { key: 'limited_risk', label: 'Limited risk' },
  { key: 'minimal_risk', label: 'Minimal risk' },
]

export default function InventoryView() {
  const reports = useInventory((s) => s.reports)
  const upsertReport = useInventory((s) => s.upsertReport)
  const list = useMemo(() => Object.values(reports), [reports])

  const [query, setQuery] = useState('')
  const [tierFilter, setTierFilter] = useState(new Set()) // empty = all
  const [reanalyzing, setReanalyzing] = useState({})
  const [drawerName, setDrawerName] = useState(null)
  const drawerOpenedFromState = useRef(false)

  const location = useLocation()
  useEffect(() => {
    const focus = location.state?.focusName
    if (focus && !drawerOpenedFromState.current) {
      drawerOpenedFromState.current = true
      setDrawerName(focus)
    }
  }, [location.state])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return list.filter((r) => {
      if (tierFilter.size > 0 && !tierFilter.has(r.classification?.tier)) {
        return false
      }
      if (!q) return true
      const name = (r.agent?.name || '').toLowerCase()
      const domain = (r.agent?.domain || '').toLowerCase()
      return name.includes(q) || domain.includes(q)
    })
  }, [list, query, tierFilter])

  const toggleTier = (k) => {
    setTierFilter((prev) => {
      const next = new Set(prev)
      if (next.has(k)) next.delete(k)
      else next.add(k)
      return next
    })
  }

  const onCopyYaml = async (yaml) => {
    if (!yaml) return
    try {
      await navigator.clipboard.writeText(yaml)
      toast.success('Policy YAML copied to clipboard.')
    } catch {
      toast.error('Clipboard access denied.')
    }
  }

  const onReanalyze = async (report) => {
    const name = report?.agent?.name
    if (!name) return
    setReanalyzing((m) => ({ ...m, [name]: true }))
    try {
      const next = await analyze(report.agent)
      upsertReport(next)
      toast.success(`Re-analysed ${name}.`)
    } catch (err) {
      toast.error(`Re-analyse failed for ${name}: ${err?.message || 'error'}`)
    } finally {
      setReanalyzing((m) => {
        const c = { ...m }
        delete c[name]
        return c
      })
    }
  }

  if (list.length === 0) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold text-text-main">Inventory</h1>
        <div className="rounded-xl border border-dashed border-border-soft bg-bg-panel p-10 text-center">
          <p className="text-sm text-text-dim">
            No analyses yet. Start with a sample agent.
          </p>
          <Link
            to="/analyze"
            className="mt-4 inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-bg-base hover:bg-accent/90"
          >
            Go to New Analysis
          </Link>
        </div>
      </div>
    )
  }

  const drawerReport = drawerName ? reports[drawerName] : null

  return (
    <div className="space-y-4">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-semibold text-text-main">Inventory</h1>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search
              size={14}
              className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-text-dim"
            />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search name or domain"
              className="w-64 rounded-md border border-border-soft bg-bg-panel py-1.5 pl-8 pr-3 text-sm text-text-main placeholder:text-text-dim focus:border-accent focus:outline-none"
            />
          </div>
        </div>
      </header>

      <div className="flex flex-wrap gap-2">
        <FilterChip
          active={tierFilter.size === 0}
          onClick={() => setTierFilter(new Set())}
        >
          All
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

      <div className="overflow-x-auto rounded-xl border border-border-soft">
        <table className="min-w-full divide-y divide-border-soft text-sm">
          <thead className="bg-bg-panel text-text-dim">
            <tr>
              <Th>Name</Th>
              <Th>Domain</Th>
              <Th>Tier</Th>
              <Th>Articles</Th>
              <Th>Rules</Th>
              <Th>Updated</Th>
              <Th>Actions</Th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-soft bg-bg-panel/60">
            {filtered.map((r) => (
              <Row
                key={r.agent.name}
                report={r}
                onOpen={() => setDrawerName(r.agent.name)}
                onCopyYaml={() => onCopyYaml(r.policy?.yaml)}
                onReanalyze={() => onReanalyze(r)}
                reanalyzing={!!reanalyzing[r.agent.name]}
              />
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-text-dim">
                  No matches.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <DetailDrawer
        report={drawerReport}
        onClose={() => setDrawerName(null)}
      />
    </div>
  )
}

function Th({ children }) {
  return (
    <th
      scope="col"
      className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide"
    >
      {children}
    </th>
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

function Row({ report, onOpen, onCopyYaml, onReanalyze, reanalyzing }) {
  const articles = report.classification?.triggered_articles || []
  const shown = articles.slice(0, 3)
  const overflow = articles.length - shown.length
  const file = basename(report.pdf_path)
  return (
    <tr
      className="cursor-pointer hover:bg-border-soft/40"
      onClick={onOpen}
    >
      <td className="whitespace-nowrap px-4 py-2 font-medium text-text-main">
        {report.agent.name}
      </td>
      <td className="whitespace-nowrap px-4 py-2 text-text-dim">
        {report.agent.domain}
      </td>
      <td className="px-4 py-2">
        <RiskBadge tier={report.classification?.tier} size="sm" />
      </td>
      <td className="px-4 py-2">
        <div className="flex flex-wrap gap-1">
          {shown.map((a, i) => (
            <span
              key={`${a}-${i}`}
              className="rounded bg-border-soft px-1.5 py-0.5 font-mono text-[10px] text-text-main"
            >
              {a}
            </span>
          ))}
          {overflow > 0 && (
            <span className="text-[10px] text-text-dim">+{overflow} more</span>
          )}
        </div>
      </td>
      <td className="whitespace-nowrap px-4 py-2 text-text-main tabular-nums">
        {report.policy?.rules_count ?? 0}
      </td>
      <td className="whitespace-nowrap px-4 py-2 text-text-dim">
        {relativeTime(report.technical_file?.generated_at)}
      </td>
      <td
        className="whitespace-nowrap px-4 py-2"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-1.5">
          {file ? (
            <a
              href={getPdfUrl(file)}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 rounded border border-border-soft px-2 py-1 text-[11px] text-text-main hover:bg-border-soft/40"
              title="Open PDF"
            >
              <ExternalLink size={12} /> PDF
            </a>
          ) : (
            <span className="text-[11px] text-text-dim">No PDF</span>
          )}
          <button
            type="button"
            onClick={onCopyYaml}
            className="inline-flex items-center gap-1 rounded border border-border-soft px-2 py-1 text-[11px] text-text-main hover:bg-border-soft/40"
            title="Copy policy YAML"
          >
            <ClipboardCopy size={12} /> YAML
          </button>
          <button
            type="button"
            onClick={onReanalyze}
            disabled={reanalyzing}
            className={[
              'inline-flex items-center gap-1 rounded border border-border-soft px-2 py-1 text-[11px] transition-colors',
              reanalyzing
                ? 'cursor-not-allowed text-text-dim'
                : 'text-text-main hover:bg-border-soft/40',
            ].join(' ')}
            title="Re-analyze"
          >
            {reanalyzing ? (
              <Loader2 size={12} className="animate-spin" />
            ) : (
              <RotateCw size={12} />
            )}
            Re-run
          </button>
        </div>
      </td>
    </tr>
  )
}

function DetailDrawer({ report, onClose }) {
  if (!report) return null
  const { agent, classification, technical_file, policy } = report
  return (
    <div className="fixed inset-0 z-30">
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
        aria-hidden="true"
      />
      <aside className="absolute right-0 top-0 flex h-full w-full max-w-2xl flex-col bg-bg-panel shadow-2xl ring-1 ring-border-soft">
        <header className="flex items-start justify-between border-b border-border-soft p-4">
          <div>
            <div className="text-xs uppercase tracking-wide text-text-dim">
              {agent.domain}
            </div>
            <div className="text-lg font-semibold text-text-main">
              {agent.name}
            </div>
            <div className="mt-2">
              <RiskBadge tier={classification?.tier} size="sm" />
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-text-dim hover:text-text-main"
            aria-label="Close drawer"
          >
            <X size={18} />
          </button>
        </header>

        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          <Section title="Classification">
            <p className="text-sm text-text-main">
              {classification?.rationale || '—'}
            </p>
            {classification?.obligations?.length > 0 && (
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-text-main">
                {classification.obligations.map((o, i) => (
                  <li key={i}>{o}</li>
                ))}
              </ul>
            )}
            {classification?.triggered_articles?.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {classification.triggered_articles.map((a, i) => (
                  <span
                    key={`${a}-${i}`}
                    className="rounded-full bg-border-soft px-2 py-0.5 font-mono text-[11px] text-text-main"
                  >
                    {a}
                  </span>
                ))}
              </div>
            )}
          </Section>

          <Section title={`Article 11 sections (${technical_file?.sections?.length || 0})`}>
            <SectionsAccordion sections={technical_file?.sections || []} />
          </Section>

          <Section title="FRIA summary">
            <p className="whitespace-pre-line text-sm text-text-main">
              {technical_file?.fria_summary || '—'}
            </p>
          </Section>

          <Section title="Datasheet">
            <DatasheetTable data={technical_file?.datasheet || {}} />
          </Section>

          <Section title={`Lobster Trap policy (${policy?.rules_count || 0} rules)`}>
            <pre className="max-h-96 overflow-auto rounded bg-bg-base p-3 font-mono text-xs leading-relaxed text-text-main">
              {policy?.yaml || '(empty)'}
            </pre>
          </Section>
        </div>
      </aside>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <section>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-text-dim">
        {title}
      </h3>
      <div className="mt-2 rounded-lg border border-border-soft bg-bg-base/40 p-3">
        {children}
      </div>
    </section>
  )
}

function SectionsAccordion({ sections }) {
  const [openIdx, setOpenIdx] = useState(null)
  if (sections.length === 0) {
    return <p className="text-sm text-text-dim">No sections.</p>
  }
  return (
    <ul className="divide-y divide-border-soft">
      {sections.map((s, i) => {
        const open = openIdx === i
        return (
          <li key={i}>
            <button
              type="button"
              onClick={() => setOpenIdx(open ? null : i)}
              className="flex w-full items-center justify-between py-2 text-left"
            >
              <span className="text-sm font-medium text-text-main">
                {s.heading}
              </span>
              <span className="text-xs text-text-dim">
                {open ? 'Hide' : 'Show'}
              </span>
            </button>
            {open && (
              <p className="whitespace-pre-line pb-3 text-sm text-text-main">
                {s.body}
              </p>
            )}
          </li>
        )
      })}
    </ul>
  )
}

function DatasheetTable({ data }) {
  const entries = Object.entries(data)
  if (entries.length === 0) {
    return <p className="text-sm text-text-dim">Empty datasheet.</p>
  }
  return (
    <table className="w-full text-sm">
      <tbody className="divide-y divide-border-soft">
        {entries.map(([k, v]) => (
          <tr key={k}>
            <td className="py-1.5 pr-3 align-top font-mono text-xs text-text-dim">
              {k}
            </td>
            <td className="py-1.5 text-text-main">
              {typeof v === 'string' ? v : JSON.stringify(v)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
