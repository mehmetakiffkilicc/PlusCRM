import React from 'react'
import ReactDOM from 'react-dom/client'
import { MantineProvider } from '@mantine/core'
import { Notifications } from '@mantine/notifications'
import '@mantine/core/styles.css'
import '@mantine/notifications/styles.css'
import App from './App'
import './index.css'
import { useThemeStore } from './stores/themeStore'
import { getTheme } from './theme'

// Global error handling for early boot issues
window.onerror = function(message, source, lineno, colno, error) {
  console.error("GLOBAL ERROR DETECTED:", message, "at", source, ":", lineno, ":", colno, error);
};

window.onunhandledrejection = function(event) {
  console.error("UNHANDLED PROMISE REJECTION:", event.reason);
};

function ThemedApp() {
  const { activeTheme, colorScheme } = useThemeStore()
  const currentTheme = getTheme(activeTheme)

  return (
    <MantineProvider key={`${activeTheme}-${colorScheme}`} theme={currentTheme} forceColorScheme={colorScheme}>
      <Notifications position="top-right" zIndex={2000} />
      <App />
    </MantineProvider>
  )
}

try {
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <ThemedApp />
    </React.StrictMode>
  )
} catch (error) {
  console.error("CRITICAL MOUNT ERROR:", error);
}
