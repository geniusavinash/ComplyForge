// Static, JIT-friendly class table for the 8 Lobster Trap actions.
const ACTION_CLASSES = {
  DENY: 'bg-risk-prohibited text-white',
  QUARANTINE: 'bg-risk-prohibited text-white',
  HUMAN_REVIEW: 'bg-risk-high text-white',
  RATE_LIMIT: 'bg-risk-limited text-white',
  MODIFY: 'bg-risk-limited text-white',
  REDIRECT: 'bg-risk-limited text-white',
  LOG: 'bg-border-soft text-text-dim',
  ALLOW: 'bg-risk-minimal text-white',
}

export default function ActionChip({ action }) {
  const cls = ACTION_CLASSES[action] || 'bg-border-soft text-text-dim'
  return (
    <span
      className={[
        'inline-flex items-center rounded-md px-2 py-0.5 text-[11px]',
        'font-mono font-semibold uppercase tracking-wide',
        cls,
      ].join(' ')}
    >
      {action || 'UNKNOWN'}
    </span>
  )
}
