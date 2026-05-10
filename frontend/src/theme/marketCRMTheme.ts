import { createTheme, MantineColorsTuple } from '@mantine/core'

const tealColors: MantineColorsTuple = [
  '#f0fdfa',
  '#ccfbf1',
  '#99f6e4',
  '#5eead4',
  '#2dd4bf',
  '#14b8a6',
  '#0d9488',
  '#0f766e',
  '#115e59',
  '#134e4a',
]

const amberColors: MantineColorsTuple = [
  '#fffbeb',
  '#fef3c7',
  '#fde68a',
  '#fcd34d',
  '#fbbf24',
  '#f59e0b',
  '#d97706',
  '#b45309',
  '#92400e',
  '#78350f',
]

const marketCRMTheme = createTheme({
  primaryColor: 'teal',
  primaryShade: 7,
  fontFamily:
    "'Open Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  fontFamilyMonospace: "ui-monospace, SFMono-Regular, Menlo, monospace",
  defaultRadius: 10,
  headings: {
    fontFamily:
      "'Poppins', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    fontWeight: '600',
  },
  colors: {
    teal: tealColors,
    amber: amberColors,
  },
  shadows: {
    xs: '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
    sm: '0 4px 6px rgba(0,0,0,0.07), 0 2px 4px rgba(0,0,0,0.06)',
    md: '0 10px 15px rgba(0,0,0,0.08), 0 4px 6px rgba(0,0,0,0.05)',
    lg: '0 20px 25px rgba(0,0,0,0.10), 0 8px 10px rgba(0,0,0,0.06)',
    xl: '0 25px 50px rgba(0,0,0,0.15), 0 10px 20px rgba(0,0,0,0.08)',
  },
  components: {
    Text: {
      defaultProps: { size: 'sm' },
      styles: () => ({
        root: {
          '&[data-dimmed]': { color: '#94a3b8' },
        },
      }),
    },
    Card: {
      defaultProps: { radius: 12, shadow: 'sm', withBorder: true },
    },
    Button: {
      defaultProps: { radius: 10 },
      styles: () => ({
        root: {
          fontWeight: 600,
          letterSpacing: '0.3px',
          transition: 'all 0.2s ease',
        },
      }),
    },
    Paper: {
      defaultProps: { radius: 12, shadow: 'sm', withBorder: true },
    },
    TextInput: {
      defaultProps: { radius: 10 },
      styles: () => ({
        input: {
          transition: 'all 0.2s ease',
          '&:focus': {
            borderColor: '#0f766e',
            boxShadow: '0 0 0 3px rgba(15, 118, 110, 0.15)',
          },
        },
      }),
    },
    Select: {
      defaultProps: { radius: 10 },
      styles: () => ({
        input: {
          transition: 'all 0.2s ease',
          '&:focus': {
            borderColor: '#0f766e',
            boxShadow: '0 0 0 3px rgba(15, 118, 110, 0.15)',
          },
        },
      }),
    },
    Table: {
      defaultProps: { highlightOnHover: true, withTableBorder: true, withColumnBorders: false },
      styles: () => ({
        table: {
          borderRadius: 12,
          overflow: 'hidden',
        },
        th: {
          fontWeight: 600,
          fontSize: '0.8rem',
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
          color: '#64748b',
        },
        td: {
          fontSize: '0.9rem',
        },
      }),
    },
    Badge: {
      defaultProps: { radius: 'xl', variant: 'light' },
      styles: () => ({
        root: {
          fontWeight: 600,
          letterSpacing: '0.3px',
        },
      }),
    },
    Tabs: {
      styles: () => ({
        tab: {
          fontWeight: 600,
          fontSize: '0.85rem',
          transition: 'all 0.2s ease',
          '&[data-active]': {
            color: '#0f766e',
          },
        },
        tabLabel: {
          color: 'inherit',
        },
      }),
    },
    Modal: {
      defaultProps: { radius: 16, padding: 'lg' },
    },
    Switch: {
      styles: () => ({
        track: {
          '&[data-checked]': {
            background: '#0f766e',
          },
        },
      }),
    },
    SegmentedControl: {
      styles: () => ({
        root: {
          borderRadius: 10,
        },
        indicator: {
          background: '#0f766e',
          borderRadius: 8,
        },
        label: {
          fontWeight: 600,
          fontSize: '0.8rem',
          '&[data-active]': {
            color: '#ffffff',
          },
        },
      }),
    },
    Tooltip: {
      defaultProps: { radius: 8 },
    },
    Notification: {
      defaultProps: { radius: 12 },
    },
    Alert: {
      defaultProps: { radius: 12 },
    },
  },
})

export default marketCRMTheme
