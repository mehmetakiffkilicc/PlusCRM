import React from 'react'

type InlineSpinnerProps = {
  size?: number
  thickness?: number
  color?: string
  trackColor?: string
}

export default function InlineSpinner({
  size = 16,
  thickness = 3,
  color = '#6366f1',
  trackColor = '#e5e7eb'
}: InlineSpinnerProps) {
  return (
    <>
      <span
        aria-hidden="true"
        style={{
          width: size,
          height: size,
          border: `${thickness}px solid ${trackColor}`,
          borderTopColor: color,
          borderRadius: '50%',
          display: 'inline-block',
          animation: 'inlineSpin 1s linear infinite'
        }}
      />
      <style>{`
        @keyframes inlineSpin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </>
  )
}
