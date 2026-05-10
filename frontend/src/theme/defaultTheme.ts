import { createTheme, MantineColorsTuple } from '@mantine/core'

const indigoColors: MantineColorsTuple = [
  '#eef2ff',
  '#e0e7ff',
  '#c7d2fe',
  '#a5b4fc',
  '#818cf8',
  '#6366f1',
  '#4f46e5',
  '#4338ca',
  '#3730a3',
  '#312e81',
]

const defaultTheme = createTheme({
  primaryColor: 'indigo',
  fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  fontFamilyMonospace: "ui-monospace, SFMono-Regular, Menlo, monospace",
  defaultRadius: 'md',
  headings: {
    fontFamily: "'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    fontWeight: '700',
  },
  colors: {
    indigo: indigoColors,
  },
  shadows: {
    xs: '0 1px 2px rgba(0,0,0,0.1)',
    sm: '0 4px 8px rgba(0,0,0,0.12)',
    md: '0 8px 16px rgba(0,0,0,0.14)',
    lg: '0 16px 32px rgba(0,0,0,0.16)',
    xl: '0 24px 48px rgba(0,0,0,0.2)',
  },
  components: {
    Text: {
      defaultProps: {
        size: 'sm',
      },
      styles: () => ({
        root: {
          '&[data-dimmed]': {
            color: '#a1a1aa',
          },
        },
      }),
    },
    Card: {
      defaultProps: {
        radius: 'lg',
        shadow: 'sm',
        withBorder: true,
      },
    },
  },
})

export default defaultTheme
