import { Ban, AlertTriangle, Info, CheckCircle2 } from 'lucide-react'

// Static class lookup so Tailwind JIT scans every utility we use.
const TIER_BG = {
  prohibited: 'bg-risk-prohibited',
  high_risk: 'bg-risk-high',
  limited_risk: 'bg-risk-limited',
  minimal_risk: 'bg-risk-minimal',
}

const TIER_LABEL = {
  prohibited: 'PROHIBITED',
  high_risk: 'HIGH RISK',
  limited_risk: 'LIMITED RISK',
  minimal_risk: 'MINIMAL RISK',
}

const TIER_ICON = {
  prohibited: Ban,
  high_risk: AlertTriangle,
  limited_risk: Info,
  minimal_risk: CheckCircle2,
}

const SIZES = {
  sm: { wrap: 'px-2 py-0.5 text-[10px] gap-1', icon: 12 },
  md: { wrap: 'px-3 py-1 text-xs gap-1.5', icon: 14 },
  lg: { wrap: 'px-4 py-1.5 text-sm gap-2', icon: 18 },
}

export default function RiskBadge({ tier, size = 'md' }) {
  const bg = TIER_BG[tier] || 'bg-border-soft'
  const label = TIER_LABEL[tier] || (tier ? String(tier).toUpperCase() : 'UNKNOWN')
  const Icon = TIER_ICON[tier] || Info
  const s = SIZES[size] || SIZES.md
  return (
    <span
      className={[
        'inline-flex items-center rounded-full font-semibold uppercase tracking-wide text-white',
        'shadow-[0_1px_0_rgba(0,0,0,0.25)]',
        bg,
        s.wrap,
      ].join(' ')}
      style={{ textShadow: '0 1px 1px rgba(0,0,0,0.35)' }}
    >
      <Icon size={s.icon} aria-hidden="true" />
      <span>{label}</span>
    </span>
  )
}
