import { Check, AlertCircle } from 'lucide-react'

/**
 * Vertical step indicator.
 *
 * @param {object} props
 * @param {{key: string, label: string}[]} props.steps
 * @param {string|null} props.currentStep   - key of the in-progress step, or null when idle/done
 * @param {string|null} [props.error]
 * @param {Object<string, number>} [props.elapsed] - optional elapsed seconds keyed by step key
 * @param {boolean} [props.allDone]         - true once the pipeline reports the final `done` event
 */
export default function StepProgress({
  steps,
  currentStep,
  error = null,
  elapsed = {},
  allDone = false,
}) {
  const currentIndex =
    currentStep == null ? -1 : steps.findIndex((s) => s.key === currentStep)

  return (
    <ol className="space-y-3">
      {steps.map((step, idx) => {
        let state
        if (error && idx === currentIndex) state = 'error'
        else if (allDone) state = 'completed'
        else if (idx < currentIndex) state = 'completed'
        else if (idx === currentIndex) state = 'current'
        else state = 'upcoming'

        const elapsedSec = elapsed[step.key]

        return (
          <li key={step.key} className="flex items-start gap-3">
            <div className="flex flex-col items-center">
              <Circle state={state} />
              {idx < steps.length - 1 && (
                <div
                  className={[
                    'mt-1 h-6 w-px transition-colors duration-300',
                    state === 'completed'
                      ? 'bg-accent'
                      : 'bg-border-soft',
                  ].join(' ')}
                />
              )}
            </div>
            <div className="flex-1 pb-2">
              <div
                className={[
                  'text-sm font-medium transition-colors duration-300',
                  state === 'upcoming' ? 'text-text-dim' : 'text-text-main',
                  state === 'error' ? 'text-risk-prohibited' : '',
                ].join(' ')}
              >
                {step.label}
              </div>
              {state === 'current' && !error && (
                <div className="text-xs text-text-dim">in progress…</div>
              )}
              {state === 'completed' && elapsedSec != null && (
                <div className="text-xs text-text-dim">
                  {elapsedSec.toFixed(1)} s
                </div>
              )}
              {state === 'error' && error && (
                <div className="text-xs text-risk-prohibited">{error}</div>
              )}
            </div>
          </li>
        )
      })}
    </ol>
  )
}

function Circle({ state }) {
  if (state === 'completed') {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-accent text-bg-base transition-all duration-300">
        <Check size={14} strokeWidth={3} />
      </span>
    )
  }
  if (state === 'current') {
    return (
      <span className="relative flex h-6 w-6 items-center justify-center">
        <span className="absolute inset-0 animate-ping rounded-full bg-accent/40" />
        <span className="relative h-3 w-3 rounded-full bg-accent" />
      </span>
    )
  }
  if (state === 'error') {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-risk-prohibited text-white">
        <AlertCircle size={14} strokeWidth={3} />
      </span>
    )
  }
  return (
    <span className="h-6 w-6 rounded-full border-2 border-border-soft bg-bg-panel" />
  )
}
