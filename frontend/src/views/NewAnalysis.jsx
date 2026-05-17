import { useEffect, useMemo, useRef, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import {
  Activity,
  Brain,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  FileText,
  Info,
  Loader2,
  RotateCcw,
  Send,
  ShieldAlert,
  ShieldCheck,
  UploadCloud,
} from 'lucide-react'
import RiskBadge from '../components/RiskBadge'
import StepProgress from '../components/StepProgress'
import { deployPolicy, getSampleAgents, streamAnalyze } from '../api/client'
import { useInventory } from '../store/inventory'
import { toast } from '../store/toasts'
import { basename } from '../lib/format'

const STEPS = [
  { key: 'classifying', label: 'Classify against EU AI Act' },
  { key: 'generating_docs', label: 'Generate Article 11 technical file' },
  { key: 'generating_policy', label: 'Generate Lobster Trap policy' },
  { key: 'rendering_pdf', label: 'Render PDF' },
]

const REQUIRED_KEYS = ['name', 'purpose', 'domain']

const TIER_FILL = {
  prohibited: 'bg-risk-prohibited',
  high_risk: 'bg-risk-high',
  limited_risk: 'bg-risk-limited',
  minimal_risk: 'bg-risk-minimal',
}

function validateDescriptor(obj) {
  if (!obj || typeof obj !== 'object' || Array.isArray(obj)) {
    return { ok: false, error: 'Expected a JSON object.' }
  }
  for (const k of REQUIRED_KEYS) {
    if (typeof obj[k] !== 'string' || !obj[k].trim()) {
      return { ok: false, error: `Missing required string field: "${k}".` }
    }
  }
  return {
    ok: true,
    value: {
      name: obj.name,
      purpose: obj.purpose,
      domain: obj.domain,
      inputs: Array.isArray(obj.inputs) ? obj.inputs : [],
      outputs: Array.isArray(obj.outputs) ? obj.outputs : [],
      affects_humans:
        typeof obj.affects_humans === 'boolean' ? obj.affects_humans : true,
      sample_prompts: Array.isArray(obj.sample_prompts)
        ? obj.sample_prompts
        : [],
      tools: Array.isArray(obj.tools) ? obj.tools : [],
    },
  }
}

export default function NewAnalysis() {
  const upsertReport = useInventory((s) => s.upsertReport)

  // Tabs
  const [tab, setTab] = useState('samples') // 'samples' | 'upload'

  // Sample agents
  const [samples, setSamples] = useState([])
  const [samplesError, setSamplesError] = useState(null)
  useEffect(() => {
    let cancelled = false
    getSampleAgents()
      .then((data) => {
        if (cancelled) return
        setSamples(Array.isArray(data) ? data : [])
      })
      .catch((err) => {
        if (cancelled) return
        setSamplesError(err?.message || 'Failed to load sample agents')
      })
    return () => {
      cancelled = true
    }
  }, [])

  // Upload
  const [uploaded, setUploaded] = useState(null)
  const [uploadError, setUploadError] = useState(null)

  const onDrop = (files) => {
    setUploadError(null)
    const f = files?.[0]
    if (!f) return
    const reader = new FileReader()
    reader.onload = () => {
      try {
        const obj = JSON.parse(String(reader.result))
        const v = validateDescriptor(obj)
        if (!v.ok) {
          setUploaded(null)
          setUploadError(v.error)
          return
        }
        setUploaded(v.value)
        setSelectedName(null)
      } catch (err) {
        setUploaded(null)
        setUploadError(err?.message || 'JSON parse error')
      }
    }
    reader.readAsText(f)
  }

  const dropzone = useDropzone({
    onDrop,
    accept: { 'application/json': ['.json'] },
    multiple: false,
  })

  const [selectedName, setSelectedName] = useState(null)

  const selectedAgent = useMemo(() => {
    if (tab === 'upload') return uploaded
    return samples.find((a) => a.name === selectedName) || null
  }, [tab, samples, selectedName, uploaded])

  // Pipeline state
  const [running, setRunning] = useState(false)
  const [currentStep, setCurrentStep] = useState(null)
  const [elapsed, setElapsed] = useState({})
  const [error, setError] = useState(null)
  const [report, setReport] = useState(null)
  const stepStartRef = useRef({})
  const abortRef = useRef(null)

  const onRun = (descriptor) => {
    if (!descriptor) return
    setRunning(true)
    setCurrentStep(null)
    setElapsed({})
    setError(null)
    setReport(null)
    stepStartRef.current = {}

    abortRef.current = streamAnalyze(
      descriptor,
      (ev) => {
        if (!ev) return
        const { step, status, payload } = ev
        if (!step) return
        if (step === 'done' && status === 'completed' && payload) {
          setReport(payload)
          setCurrentStep(null)
          setRunning(false)
          try {
            upsertReport(payload)
          } catch {
            // non-fatal
          }
          return
        }
        if (status === 'started') {
          stepStartRef.current[step] = performance.now()
          setCurrentStep(step)
        } else if (status === 'completed') {
          const start = stepStartRef.current[step]
          if (start != null) {
            const sec = (performance.now() - start) / 1000
            setElapsed((prev) => ({ ...prev, [step]: sec }))
          }
        }
      },
      undefined,
      (err) => {
        setError(err?.message || 'Analysis failed')
        setRunning(false)
      },
    )
  }

  const onCancel = () => {
    abortRef.current?.abort()
    setRunning(false)
    setCurrentStep(null)
  }

  useEffect(() => () => abortRef.current?.abort(), [])

  const lastDescriptorRef = useRef(null)
  useEffect(() => {
    if (selectedAgent) lastDescriptorRef.current = selectedAgent
  }, [selectedAgent])

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-text-main">New Analysis</h1>
        <p className="text-sm text-text-dim">
          Pick a sample agent or drop an AgentDescriptor JSON. ComplyForge will
          classify, document, and emit a Lobster Trap policy in parallel.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* LEFT — input */}
        <section className="rounded-xl border border-border-soft bg-bg-panel p-5">
          <div className="mb-4 flex gap-2">
            <TabButton active={tab === 'samples'} onClick={() => setTab('samples')}>
              Sample agents
            </TabButton>
            <TabButton active={tab === 'upload'} onClick={() => setTab('upload')}>
              Upload JSON
            </TabButton>
          </div>

          {tab === 'samples' && (
            <div>
              {samplesError && (
                <p className="mb-3 text-sm text-risk-prohibited">
                  {samplesError}
                </p>
              )}
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {samples.map((a) => {
                  const selected = selectedName === a.name
                  return (
                    <button
                      key={a.name}
                      type="button"
                      onClick={() => {
                        setSelectedName(a.name)
                        setUploaded(null)
                      }}
                      className={[
                        'rounded-lg border p-4 text-left transition-colors',
                        selected
                          ? 'border-accent bg-bg-base ring-2 ring-accent'
                          : 'border-border-soft bg-bg-base/40 hover:border-text-dim',
                      ].join(' ')}
                    >
                      <div className="font-semibold text-text-main">
                        {a.name}
                      </div>
                      <div className="mt-0.5 text-xs text-text-dim">
                        {a.domain}
                      </div>
                      <div className="mt-2 text-xs text-text-dim">
                        {(a.sample_prompts || []).length} prompts ·{' '}
                        {(a.tools || []).length} tools
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          {tab === 'upload' && (
            <div>
              <div
                {...dropzone.getRootProps()}
                className={[
                  'flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 text-center transition-colors',
                  dropzone.isDragActive
                    ? 'border-accent bg-accent/10'
                    : 'border-border-soft bg-bg-base/40 hover:border-text-dim',
                ].join(' ')}
              >
                <input {...dropzone.getInputProps()} />
                <UploadCloud className="text-text-dim" size={28} />
                <div className="mt-2 text-sm text-text-main">
                  Drop an AgentDescriptor .json file here
                </div>
                <div className="text-xs text-text-dim">
                  Required keys: name, purpose, domain
                </div>
              </div>
              {uploadError && (
                <p className="mt-3 text-sm text-risk-prohibited">{uploadError}</p>
              )}
              {uploaded && (
                <p className="mt-3 text-sm text-risk-minimal">
                  Loaded {uploaded.name}.
                </p>
              )}
            </div>
          )}

          <Preview agent={selectedAgent} />

          <div className="mt-5 flex items-center gap-3">
            <button
              type="button"
              onClick={() => onRun(selectedAgent)}
              disabled={!selectedAgent || running}
              className={[
                'inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-colors',
                !selectedAgent || running
                  ? 'cursor-not-allowed bg-border-soft text-text-dim'
                  : 'bg-accent text-bg-base hover:bg-accent/90',
              ].join(' ')}
            >
              {running ? (
                <>
                  <Loader2 size={16} className="animate-spin" /> Analyzing…
                </>
              ) : (
                <>
                  <Send size={16} /> Run Compliance Analysis
                </>
              )}
            </button>
            {running && (
              <button
                type="button"
                onClick={onCancel}
                className="text-xs text-text-dim hover:text-text-main"
              >
                Cancel
              </button>
            )}
          </div>
        </section>

        {/* RIGHT — result */}
        <section className="rounded-xl border border-border-soft bg-bg-panel p-5">
          {!running && !report && !error && <HowItWorks />}

          {(running || error) && (
            <div>
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-text-dim">
                Pipeline
              </h2>
              <StepProgress
                steps={STEPS}
                currentStep={currentStep}
                error={error}
                elapsed={elapsed}
              />
              {error && (
                <div className="mt-4 rounded-lg border border-risk-prohibited/60 bg-risk-prohibited/15 p-3">
                  <div className="text-sm font-medium text-risk-prohibited">
                    {error}
                  </div>
                  <button
                    type="button"
                    onClick={() =>
                      onRun(lastDescriptorRef.current || selectedAgent)
                    }
                    className="mt-2 inline-flex items-center gap-1 text-xs text-accent hover:underline"
                  >
                    <RotateCcw size={12} /> Retry
                  </button>
                </div>
              )}
            </div>
          )}

          {!running && report && <ReportPanel report={report} />}
        </section>
      </div>
    </div>
  )
}

function TabButton({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        'rounded-md px-3 py-1.5 text-sm transition-colors',
        active
          ? 'bg-accent text-bg-base'
          : 'text-text-dim hover:bg-border-soft/40 hover:text-text-main',
      ].join(' ')}
    >
      {children}
    </button>
  )
}

function Preview({ agent }) {
  if (!agent) {
    return (
      <div className="mt-5 rounded-lg border border-dashed border-border-soft p-4 text-sm text-text-dim">
        Pick or upload an agent to preview the descriptor.
      </div>
    )
  }
  return (
    <div className="mt-5 rounded-lg border border-border-soft bg-bg-base/40 p-4">
      <div className="text-sm font-semibold text-text-main">{agent.name}</div>
      <div className="text-xs text-text-dim">{agent.domain}</div>
      <p className="mt-2 text-sm text-text-main">{agent.purpose}</p>
      {agent.sample_prompts?.length > 0 && (
        <div className="mt-3">
          <div className="text-xs uppercase tracking-wide text-text-dim">
            Sample prompts
          </div>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-xs text-text-main">
            {agent.sample_prompts.slice(0, 4).map((p, i) => (
              <li key={i} className="truncate">
                {p}
              </li>
            ))}
          </ul>
        </div>
      )}
      {agent.tools?.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {agent.tools.map((t) => (
            <span
              key={t}
              className="rounded bg-border-soft px-2 py-0.5 font-mono text-[11px] text-text-main"
            >
              {t}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

function HowItWorks() {
  const items = [
    {
      Icon: ShieldAlert,
      title: 'Classify',
      body: 'EU AI Act tier from Articles 5/6, Annex III, Article 50.',
    },
    {
      Icon: FileText,
      title: 'Document',
      body: 'Article 11 technical file + FRIA + datasheet.',
    },
    {
      Icon: Brain,
      title: 'Policy',
      body: 'Veea Lobster Trap YAML, real-schema rules.',
    },
    {
      Icon: ShieldCheck,
      title: 'Enforce',
      body: 'Live proxy denies, logs, escalates.',
    },
  ]
  return (
    <div>
      <h2 className="text-sm font-semibold uppercase tracking-wide text-text-dim">
        How it works
      </h2>
      <ol className="mt-3 grid grid-cols-2 gap-3">
        {items.map(({ Icon, title, body }, i) => (
          <li
            key={title}
            className="rounded-lg border border-border-soft bg-bg-base/40 p-4"
          >
            <div className="flex items-center gap-2 text-text-dim">
              <span className="text-xs font-mono">0{i + 1}</span>
              <Icon size={16} />
            </div>
            <div className="mt-1 font-semibold text-text-main">{title}</div>
            <div className="text-xs text-text-dim">{body}</div>
          </li>
        ))}
      </ol>
      <div className="mt-4 flex items-center gap-2 text-xs text-text-dim">
        <Activity size={14} /> Steps stream live as the orchestrator runs.
      </div>
    </div>
  )
}

function ReportPanel({ report }) {
  const tier = report.classification?.tier
  const confidencePct = Math.round((report.classification?.confidence || 0) * 100)
  const fillClass = TIER_FILL[tier] || 'bg-accent'

  return (
    <div className="space-y-5">
      <div className="rounded-lg border border-border-soft bg-bg-base/40 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-xs uppercase tracking-wide text-text-dim">
              Classification result
            </div>
            <div className="mt-1 text-lg font-semibold text-text-main">
              {report.agent.name}
            </div>
          </div>
          <RiskBadge tier={tier} size="lg" />
        </div>
        <div className="mt-3">
          <div className="flex items-center justify-between text-xs text-text-dim">
            <span>Confidence</span>
            <span className="font-mono">{confidencePct}%</span>
          </div>
          <div className="mt-1 h-2 rounded-full bg-border-soft">
            <div
              className={['h-2 rounded-full transition-all', fillClass].join(' ')}
              style={{ width: `${confidencePct}%` }}
            />
          </div>
        </div>
        {report.classification?.triggered_articles?.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1">
            {report.classification.triggered_articles.map((a, i) => (
              <span
                key={`${a}-${i}`}
                className="rounded-full bg-border-soft px-2 py-0.5 font-mono text-[11px] text-text-main"
              >
                {a}
              </span>
            ))}
          </div>
        )}
      </div>

      <Collapsible title="Rationale">
        <p className="text-sm leading-relaxed text-text-main">
          {report.classification?.rationale || '—'}
        </p>
        {report.classification?.obligations?.length > 0 && (
          <div className="mt-3">
            <div className="text-xs uppercase tracking-wide text-text-dim">
              Obligations
            </div>
            <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-text-main">
              {report.classification.obligations.map((o, i) => (
                <li key={i}>{o}</li>
              ))}
            </ul>
          </div>
        )}
      </Collapsible>

      <DocsCard report={report} />
      <PolicyCard report={report} />
    </div>
  )
}

function DocsCard({ report }) {
  const sections = report.technical_file?.sections?.length || 0
  const file = basename(report.pdf_path)
  return (
    <div className="rounded-lg border border-border-soft bg-bg-base/40 p-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs uppercase tracking-wide text-text-dim">
            Generated documents
          </div>
          <div className="mt-1 text-sm font-medium text-text-main">
            {sections} sections · ~10–40 pages estimate
          </div>
          {file && (
            <div className="mt-1 font-mono text-xs text-text-dim">{file}</div>
          )}
        </div>
        {file ? (
          <a
            href={`http://localhost:8000${getPdfUrlFromBackend(file)}`}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 rounded-md bg-accent px-3 py-1.5 text-xs font-semibold text-bg-base hover:bg-accent/90"
          >
            <ExternalLink size={12} /> Open PDF
          </a>
        ) : (
          <span className="text-xs text-text-dim">No PDF</span>
        )}
      </div>
    </div>
  )
}

function getPdfUrlFromBackend(file) {
  // The api/client.js getPdfUrl helper already returns a full URL; we keep the
  // link logic local here to avoid yet another import for one line.
  return `/api/pdf/${encodeURIComponent(file)}`
}

function PolicyCard({ report }) {
  const [showYaml, setShowYaml] = useState(false)
  const [deploying, setDeploying] = useState(false)
  const [lastDeploy, setLastDeploy] = useState(null) // { reload_method, rule_count, ... }
  const policy = report.policy || {}

  const onDeploy = async () => {
    if (!policy?.name) return
    setDeploying(true)
    try {
      const result = await deployPolicy(policy.name)
      setLastDeploy(result)
      const reload = result?.reload_method || 'manual_restart_required'
      const ruleCount = result?.rule_count ?? policy.rules_count ?? 0
      toast.success(
        `Policy deployed → Lobster Trap will enforce ${ruleCount} rules. ` +
          `reload_method: ${reload}`,
      )
    } catch (err) {
      const status = err?.response?.status
      if (status === 404 || status === 405) {
        toast.warn(
          'Phase 10 wiring pending — policy YAML available in panel below.',
        )
      } else {
        toast.error(`Deploy failed: ${err?.message || 'unknown error'}`)
      }
    } finally {
      setDeploying(false)
    }
  }

  return (
    <div className="rounded-lg border border-border-soft bg-bg-base/40 p-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs uppercase tracking-wide text-text-dim">
            Lobster Trap policy
          </div>
          <div className="mt-1 text-sm font-medium text-text-main">
            {policy.name || '—'} · {policy.rules_count || 0} rules
          </div>
          {policy.purpose && (
            <div className="mt-0.5 text-xs text-text-dim">{policy.purpose}</div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setShowYaml((v) => !v)}
            className="inline-flex items-center gap-1 rounded-md border border-border-soft px-2 py-1 text-xs text-text-main hover:bg-border-soft/40"
          >
            {showYaml ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            YAML
          </button>
          <button
            type="button"
            onClick={onDeploy}
            disabled={deploying}
            className={[
              'inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-xs font-semibold transition-colors',
              deploying
                ? 'cursor-not-allowed bg-border-soft text-text-dim'
                : 'bg-accent text-bg-base hover:bg-accent/90',
            ].join(' ')}
          >
            {deploying ? (
              <Loader2 size={12} className="animate-spin" />
            ) : (
              <Send size={12} />
            )}
            Deploy
          </button>
        </div>
      </div>
      {lastDeploy?.reload_method === 'manual_restart_required' && (
        <div className="mt-3 flex items-start gap-2 rounded-md border border-accent/40 bg-accent/10 px-3 py-2 text-xs text-text-main">
          <Info size={14} className="mt-0.5 shrink-0 text-accent" />
          <div>
            <div className="font-semibold">Restart Lobster Trap to enforce</div>
            <div className="mt-0.5 text-text-dim">
              The Veea binary loads policies once at startup (no SIGHUP, no
              admin endpoint, no file watcher). Stop and re-run{' '}
              <span className="font-mono">.\bin\lobstertrap.exe serve …</span>{' '}
              with{' '}
              <span className="font-mono break-all">
                --policy {lastDeploy.policy_path}
              </span>{' '}
              (or include this file alongside your default policy) to pick it
              up.
            </div>
          </div>
        </div>
      )}
      {showYaml && policy.yaml && (
        <pre className="mt-3 max-h-72 overflow-auto rounded bg-bg-base p-3 font-mono text-xs leading-relaxed text-text-main">
          {policy.yaml}
        </pre>
      )}
    </div>
  )
}

function Collapsible({ title, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="rounded-lg border border-border-soft bg-bg-base/40 p-4">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between text-sm font-medium text-text-main"
      >
        <span>{title}</span>
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>
      {open && <div className="mt-3">{children}</div>}
    </div>
  )
}

// `getPdfUrlFromBackend` above keeps the link logic local so this view doesn't
// need a second import; the canonical absolute-URL builder lives in
// `../api/client.js` and is used by views that need it directly.
