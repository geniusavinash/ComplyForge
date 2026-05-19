import { useState } from 'react'
import {
  Brain,
  ChevronDown,
  ChevronUp,
  Info,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react'

/**
 * Reasoning trace panel.
 *
 * @param {object} props
 * @param {object} props.classification - ClassificationResult
 * @param {object|null} [props.critique] - CriticReview | null
 */

const TIER_FILL = {
  prohibited: 'bg-risk-prohibited',
  high_risk: 'bg-risk-high',
  limited_risk: 'bg-risk-limited',
  minimal_risk: 'bg-risk-minimal',
}

const TIER_CHIP = {
  prohibited: 'bg-risk-prohibited/20 text-risk-prohibited',
  high_risk: 'bg-risk-high/20 text-risk-high',
  limited_risk: 'bg-risk-limited/20 text-risk-limited',
  minimal_risk: 'bg-risk-minimal/20 text-risk-minimal',
}

const TIER_LABEL = {
  prohibited: 'PROHIBITED',
  high_risk: 'HIGH_RISK',
  limited_risk: 'LIMITED_RISK',
  minimal_risk: 'MINIMAL_RISK',
}

function describeDelta(delta) {
  const pct = Math.round(delta * 100)
  if (pct === 0) return 'no change'
  const direction = pct > 0 ? 'raised' : 'lowered'
  return `Critic ${direction} confidence by ${Math.abs(pct)} percentage points.`
}

export default function ReasoningTrace({ classification, critique = null }) {
  const [open, setOpen] = useState(false)

  if (!classification) return null

  const tier = classification.tier
  const confidence =
    typeof classification.confidence === 'number'
      ? classification.confidence
      : 0
  const confidencePct = Math.round(confidence * 100)
  const fillClass = TIER_FILL[tier] || 'bg-accent'
  const chipClass = TIER_CHIP[tier] || 'bg-border-soft text-text-main'
  const tierLabel = TIER_LABEL[tier] || (tier || 'UNKNOWN').toUpperCase()

  const articles = classification.triggered_articles || []
  const articleCount = articles.length

  const criticAgreedText = critique
    ? critique.agreed
      ? 'Critic agreed'
      : 'Critic dissented'
    : null

  const summary = [
    `Tier: ${tierLabel}`,
    `Confidence ${confidence.toFixed(2)}`,
    criticAgreedText,
    `${articleCount} ${articleCount === 1 ? 'article' : 'articles'}`,
  ]
    .filter(Boolean)
    .join(' · ')

  return (
    <div className="rounded-lg border border-border-soft bg-bg-panel p-4">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 text-left"
      >
        <div className="flex items-center gap-2">
          <Brain size={16} className="text-accent" />
          <span className="text-sm font-semibold text-text-main">
            Reasoning trace
          </span>
          <span
            className={[
              'rounded-full px-2 py-0.5 font-mono text-[11px]',
              chipClass,
            ].join(' ')}
          >
            {summary}
          </span>
        </div>
        {open ? (
          <ChevronUp size={14} className="text-text-dim" />
        ) : (
          <ChevronDown size={14} className="text-text-dim" />
        )}
      </button>

      {open && (
        <div className="mt-4 space-y-4">
          {/* Rationale */}
          <div>
            <div className="text-xs uppercase tracking-wide text-text-dim">
              Classification rationale
            </div>
            <p
              className="mt-1 text-sm leading-relaxed text-text-main"
              style={{ whiteSpace: 'pre-wrap' }}
            >
              {classification.rationale || '—'}
            </p>
          </div>

          {/* Confidence bar */}
          <div>
            <div className="flex items-center justify-between text-xs text-text-dim">
              <span>Confidence</span>
              <span className="font-mono">{confidencePct}%</span>
            </div>
            <div className="mt-1 h-2 rounded-full bg-border-soft">
              <div
                className={['h-2 rounded-full transition-all', fillClass].join(
                  ' ',
                )}
                style={{ width: `${confidencePct}%` }}
              />
            </div>
            {critique && critique.confidence_delta !== 0 && (
              <div className="mt-2 text-xs text-text-dim">
                {describeDelta(critique.confidence_delta)}
              </div>
            )}
          </div>

          {/* Triggered articles */}
          {articles.length > 0 && (
            <div>
              <div className="text-xs uppercase tracking-wide text-text-dim">
                Triggered articles
              </div>
              <div className="mt-1 flex flex-wrap gap-1">
                {articles.map((a, i) => (
                  <span
                    key={`${a}-${i}`}
                    className={[
                      'rounded-full px-2 py-0.5 font-mono text-[11px]',
                      chipClass,
                    ].join(' ')}
                  >
                    {a}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Critic section */}
          {critique && (
            <div className="rounded-md border border-border-soft bg-bg-base/40 p-3">
              <div className="flex items-center gap-2">
                {critique.agreed ? (
                  <ShieldCheck size={14} className="text-risk-minimal" />
                ) : (
                  <ShieldAlert size={14} className="text-risk-prohibited" />
                )}
                <span
                  className={[
                    'inline-block h-2 w-2 rounded-full',
                    critique.agreed
                      ? 'bg-risk-minimal'
                      : 'bg-risk-prohibited',
                  ].join(' ')}
                />
                <span className="text-sm font-semibold text-text-main">
                  Critic verdict:{' '}
                  {critique.agreed ? 'AGREED' : 'DISSENTING'}
                </span>
              </div>

              {critique.concerns?.length > 0 && (
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-text-main">
                  {critique.concerns.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              )}

              {critique.suggestion && (
                <div className="mt-3 flex items-start gap-2 rounded-md border border-accent/40 bg-accent/10 px-3 py-2 text-xs text-text-main">
                  <Info size={14} className="mt-0.5 shrink-0 text-accent" />
                  <div>
                    <div className="font-semibold">Suggestion</div>
                    <div className="mt-0.5 text-text-dim">
                      {critique.suggestion}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
