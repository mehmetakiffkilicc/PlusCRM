import React, { memo } from 'react'

interface LoadingOverlayProps {
  loading: boolean
  children: React.ReactNode
  blockInteraction?: boolean
  dimContent?: boolean
  message?: string
}

const LoadingOverlay: React.FC<LoadingOverlayProps> = ({
  loading,
  children,
  blockInteraction = true,
  dimContent = true,
  message,
}) => {
  return (
    <div style={{ position: 'relative', minHeight: '200px', width: '100%' }}>
      {loading && (
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(248, 250, 252, 0.85)',
          backdropFilter: 'blur(2px)',
          zIndex: 50,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          gap: '12px',
          borderRadius: 'inherit',
          pointerEvents: blockInteraction ? 'auto' : 'none'
        }}>
          <div className="spinner" style={{
            width: '40px',
            height: '40px',
            border: '3px solid #e2e8f0',
            borderTop: '3px solid #6366f1',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite'
          }}></div>
          {message && (
            <div style={{ color: '#6366f1', fontWeight: 500, fontSize: '14px' }}>
              {message}
            </div>
          )}
          <style>{`
            @keyframes spin {
              0% { transform: rotate(0deg); }
              100% { transform: rotate(360deg); }
            }
          `}</style>
        </div>
      )}
      <div style={{ 
        opacity: loading && dimContent ? 0.6 : 1, 
        transition: 'opacity 0.3s ease',
        pointerEvents: loading && blockInteraction ? 'none' : 'auto'
      }}>
        {children}
      </div>
    </div>
  )
}

export default memo(LoadingOverlay)
