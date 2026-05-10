#!/usr/bin/env node
/**
 * Simple performance regression guard.
 *
 * This intentionally uses string checks (not AST) to stay dependency-free.
 * It enforces the presence of our first-load budget + idle warmup patterns.
 */

import fs from 'node:fs'
import path from 'node:path'

const root = process.cwd()

const mustContain = (filePath, needles) => {
  const abs = path.join(root, filePath)
  const content = fs.readFileSync(abs, 'utf8')
  const missing = needles.filter((n) => !content.includes(n))
  if (missing.length) {
    throw new Error(
      `perf-guard: ${filePath} is missing required patterns:\n` +
        missing.map((m) => `- ${JSON.stringify(m)}`).join('\n')
    )
  }
}

const mustMatch = (filePath, regexes) => {
  const abs = path.join(root, filePath)
  const content = fs.readFileSync(abs, 'utf8')
  const missing = regexes.filter((r) => !r.test(content))
  if (missing.length) {
    throw new Error(
      `perf-guard: ${filePath} is missing required regex patterns:\n` +
        missing.map((m) => `- ${m}`).join('\n')
    )
  }
}

try {
  // Guard the most critical file.
  mustContain('src/pages/DashboardHome.tsx', [
    // Warmup must be deferred to idle (or fallback)
    'requestIdleCallback',
    'scheduleWarmup(dsId)',

    // Initial mount must not be blocked by full-page overlay
    'const [loading, setLoading] = useState(false)',

    // Safety against stuck blur
    'setAnalyticsLoading(false)',
  ])

  // Guard app-level routing to avoid a global Suspense gate (blank/loader for long chunk fetch).
  mustContain('src/App.tsx', [
    // Must proactively preload the initial route chunk
    "void import('./pages/DashboardHome')",
    // Must not wrap the entire app in a single Suspense
    'InlineRouteLoader',
  ])

  // Guard the HTML boot skeleton to avoid blank screen on slow JS.
  mustContain('index.html', [
    'PERF: ultra-light boot skeleton',
    'Uygulama hazırlanıyor',
  ])

  mustMatch('src/pages/DashboardHome.tsx', [
    // Enforce dsId guard exists in debouncedLoadAnalytics to prevent stuck loading
    /const\s+debouncedLoadAnalytics[\s\S]*?\(\s*dsId:[^\)]*\)\s*=>\s*\{[\s\S]*?if\s*\(!dsId\)[\s\S]*?setAnalyticsLoading\(false\)/,

    // Enforce dsId guard exists in loadAnalytics to clear loading
    /const\s+loadAnalytics[\s\S]*?\(\s*dsId:[^\)]*\)\s*=>\s*\{[\s\S]*?if\s*\(!dsId\)[\s\S]*?setAnalyticsLoading\(false\)/,
  ])

  console.log('perf-guard: OK')
} catch (err) {
  console.error(String(err?.stack || err))
  process.exit(1)
}
