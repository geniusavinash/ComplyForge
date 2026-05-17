/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'bg-base': '#0B0F1A',
        'bg-panel': '#111827',
        'border-soft': '#1F2937',
        'text-main': '#E5E7EB',
        'text-dim': '#9CA3AF',
        'risk-prohibited': '#DC2626',
        'risk-high': '#EA580C',
        'risk-limited': '#CA8A04',
        'risk-minimal': '#16A34A',
        accent: '#F59E0B',
      },
    },
  },
  plugins: [],
}
