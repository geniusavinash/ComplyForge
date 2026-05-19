import { ArrowRight, Check } from 'lucide-react'

/**
 * Horizontal execution-plan flow card.
 *
 * @param {object} props
 * @param {object|null} props.plan - ExecutionPlan
 * @param {string|null} [props.currentStepId] - id of the in-flight step
 * @param {string[]} [props.completedStepIds] - ids of completed steps
 */
export default function PlanPreview({
  plan,
  currentStepId = null,
  completedStepIds = [],
}) {
  if (!plan) return null

  const steps = Array.isArray(plan.steps) ? plan.steps : []
  const completedSet = new Set(completedStepIds || [])

  return (
    <div className="rounded-lg border border-border-soft bg-bg-panel p-4">
      <div className="text-[11px] font-semibold uppercase tracking-wide text-accent">
        {plan.pipeline || 'execution_plan'}
      </div>
      {plan.rationale && (
        <p className="mt-1 text-sm text-text-main">{plan.rationale}</p>
      )}

      {steps.length > 0 && (
        <div className="mt-4">
          {/* Horizontal flow on md+ */}
          <div className="hidden items-stretch gap-2 md:flex">
            {steps.map((step, idx) => {
              const isCurrent = step.id && step.id === currentStepId
              const isCompleted = completedSet.has(step.id)
              return (
                <div key={step.id || idx} className="flex flex-1 items-stretch">
                  <StepCard
                    index={idx + 1}
                    step={step}
                    isCurrent={isCurrent}
                    isCompleted={isCompleted}
                  />
                  {idx < steps.length - 1 && (
                    <div className="flex shrink-0 items-center px-1">
                      <ArrowRight size={14} className="text-text-dim" />
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Vertical fallback on small screens */}
          <ol className="space-y-2 md:hidden">
            {steps.map((step, idx) => {
              const isCurrent = step.id && step.id === currentStepId
              const isCompleted = completedSet.has(step.id)
              return (
                <li key={step.id || idx}>
                  <StepCard
                    index={idx + 1}
                    step={step}
                    isCurrent={isCurrent}
                    isCompleted={isCompleted}
                  />
                </li>
              )
            })}
          </ol>
        </div>
      )}
    </div>
  )
}

function truncate(text, n) {
  if (!text) return ''
  return text.length > n ? `${text.slice(0, n - 1).trimEnd()}…` : text
}

function StepCard({ index, step, isCurrent, isCompleted }) {
  const ringClass = isCurrent ? 'ring-2 ring-accent' : ''
  return (
    <div
      className={[
        'flex flex-1 flex-col rounded-md border border-border-soft bg-bg-base/40 p-3',
        ringClass,
      ].join(' ')}
    >
      <div className="flex items-center justify-between">
        <div className="flex h-5 w-5 items-center justify-center rounded-full bg-border-soft text-[11px] font-mono text-text-main">
          {index}
        </div>
        {isCompleted && <Check size={14} className="text-accent" />}
      </div>
      <div className="mt-2 text-xs text-text-main">
        {truncate(step.description, 70)}
      </div>
      {typeof step.expected_duration_seconds === 'number' && (
        <div className="mt-2 text-[11px] text-text-dim">
          ~{step.expected_duration_seconds}s
        </div>
      )}
    </div>
  )
}
