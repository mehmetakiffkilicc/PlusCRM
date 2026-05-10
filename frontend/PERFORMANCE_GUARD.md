# Performance Guard (DO NOT REGRESS)

This project is tuned for fast *first open* and stable UX.

## Non‑negotiable rules

### 1) First paint must not be blocked
- The app must become usable within ~2–3 seconds on typical hardware/network.
- The initial mount must **not** be held behind a full-page blur overlay.
- Heavy work (warmups, prefetch, chart libraries, heavy analytics calls) must be **deferred** and must not block first paint.

### 2) Keep the initialization contract in `DashboardHome`
Critical invariants in `src/pages/DashboardHome.tsx`:
- `initializeApp` must:
  - kick off datasource/dashboard fetch
  - never block the UI with a full-page overlay
  - defer warmup/prefetch work to `requestIdleCallback` (or delayed timeout fallback)
- `loading` overlay is reserved for explicit user actions (e.g., widget operations), not initial mount.

### 3) Warmup/prefetch must be deferred
- Warmup *chunks* and heavy endpoints must run only after first paint:
  - via `requestIdleCallback(..., { timeout: 4000 })` when available
  - or a delayed `setTimeout` fallback

### 4) Never leave loading/blur states stuck
- Any async analytics fetch must guarantee `analyticsLoading` is cleared.
- `debouncedLoadAnalytics` and `loadAnalytics` must never set loading true when `dsId` is empty.

## Automated guard

Run:
- `npm run perf:guard`

This script checks the existence of the performance-critical constants/patterns.
If it fails, it means a change risks regressing first-load performance.

## How to add features safely
- Prefer `React.lazy` + `Suspense` for heavy pages/components.
- Avoid importing chart libs in the initial route unless truly needed.
- If new work must happen on startup, schedule it idle/after paint.
