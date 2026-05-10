import defaultTheme from './defaultTheme'
import marketCRMTheme from './marketCRMTheme'
import type { ActiveTheme } from '../stores/themeStore'

export function getTheme(activeTheme: ActiveTheme) {
  return activeTheme === 'marketCRM' ? marketCRMTheme : defaultTheme
}

export { defaultTheme, marketCRMTheme }
