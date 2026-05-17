import { X } from 'lucide-react'
import { useToasts } from '../store/toasts'

const KIND_CLASSES = {
  info: 'border-border-soft bg-bg-panel text-text-main',
  success: 'border-risk-minimal/60 bg-risk-minimal/15 text-text-main',
  warn: 'border-risk-limited/60 bg-risk-limited/15 text-text-main',
  error: 'border-risk-prohibited/60 bg-risk-prohibited/15 text-text-main',
}

export default function Toaster() {
  const toasts = useToasts((s) => s.toasts)
  const dismiss = useToasts((s) => s.dismiss)

  if (!toasts.length) return null

  return (
    <div className="pointer-events-none fixed right-4 top-20 z-50 flex w-80 flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={[
            'pointer-events-auto flex items-start gap-3 rounded-lg border px-3 py-2 shadow-lg',
            KIND_CLASSES[t.kind] || KIND_CLASSES.info,
          ].join(' ')}
        >
          <span className="flex-1 text-sm leading-snug">{t.message}</span>
          <button
            type="button"
            onClick={() => dismiss(t.id)}
            className="text-text-dim hover:text-text-main"
            aria-label="Dismiss"
          >
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  )
}
