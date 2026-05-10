import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type ActiveTheme = 'default' | 'marketCRM'
export type ColorScheme = 'light' | 'dark'

interface ThemeState {
  activeTheme: ActiveTheme
  colorScheme: ColorScheme
  setActiveTheme: (theme: ActiveTheme) => void
  setColorScheme: (scheme: ColorScheme) => void
  toggleColorScheme: () => void
}

export function applyDataAttribute(theme: ActiveTheme) {
  document.documentElement.setAttribute('data-theme', theme)
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      activeTheme: 'default',
      colorScheme: 'light',
      setActiveTheme: (activeTheme) => {
        applyDataAttribute(activeTheme)
        set({ activeTheme })
      },
      setColorScheme: (colorScheme) => set({ colorScheme }),
      toggleColorScheme: () =>
        set((state) => ({
          colorScheme: state.colorScheme === 'light' ? 'dark' : 'light',
        })),
    }),
    { name: 'theme-store' }
  )
)
