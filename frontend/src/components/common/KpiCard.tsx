import { ReactNode } from 'react'

interface KpiCardProps {
  gradient: string
  shadow: string
  label: string
  value: string
  sub?: string
  icon?: ReactNode
}

export function KpiCard({ gradient, shadow, label, value, sub, icon }: KpiCardProps) {
  return (
    <div style={{
      background: gradient,
      borderRadius: '16px',
      padding: '24px',
      color: 'white',
      boxShadow: `0 10px 25px -5px ${shadow}`,
      position: 'relative',
      overflow: 'hidden',
      minHeight: 120,
    }}>
      <div style={{ fontSize: '0.8rem', opacity: 0.85, marginBottom: '8px', fontWeight: 600, letterSpacing: '0.3px' }}>{label}</div>
      <div style={{ fontSize: '2rem', fontWeight: 700, lineHeight: 1.1 }}>{value}</div>
      {sub && <div style={{ fontSize: '0.75rem', opacity: 0.8, marginTop: '6px' }}>{sub}</div>}
      <div style={{ position: 'absolute', right: '-10px', bottom: '-10px', opacity: 0.12 }}>{icon}</div>
    </div>
  )
}

/* ── Renk paleti sabitleri ─────────────────────────────────────────────────── */
export const KPI_COLORS = {
  indigo: {
    gradient: 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)',
    shadow: 'rgba(79,70,229,0.35)',
  },
  green: {
    gradient: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
    shadow: 'rgba(16,185,129,0.35)',
  },
  red: {
    gradient: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
    shadow: 'rgba(239,68,68,0.35)',
  },
  amber: {
    gradient: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
    shadow: 'rgba(245,158,11,0.35)',
  },
  blue: {
    gradient: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
    shadow: 'rgba(59,130,246,0.35)',
  },
  pink: {
    gradient: 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)',
    shadow: 'rgba(236,72,153,0.35)',
  },
} as const
