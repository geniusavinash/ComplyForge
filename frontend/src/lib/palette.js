// Centralised tier hex palette.
//
// Tailwind classes are the canonical source of truth (see tailwind.config.js).
// Recharts and inline SVG props can't accept utility classes — they need raw
// color strings — so we mirror the four risk-tier hex values here exactly
// once. Keep these values in lock-step with `tailwind.config.js`.
export const TIER_HEX = Object.freeze({
  prohibited: '#DC2626', // bg-risk-prohibited
  high_risk: '#EA580C', // bg-risk-high
  limited_risk: '#CA8A04', // bg-risk-limited
  minimal_risk: '#16A34A', // bg-risk-minimal
  unknown: '#6B7280',
})

export const PANEL_HEX = '#111827' // bg-bg-panel
export const BORDER_HEX = '#1F2937' // border-soft
export const TEXT_DIM_HEX = '#9CA3AF' // text-dim
export const TEXT_MAIN_HEX = '#E5E7EB' // text-main
export const ACCENT_HEX = '#F59E0B' // accent
