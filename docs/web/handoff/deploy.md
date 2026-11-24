# Handoff: deploy (task 6)

Branch: `deploy` · Date: 2026-11-24 · Status: done, live and checked

## URLs
- Production and preview (same deployment so far): https://saltmarket.vercel.app/
- Repo: `DhemanthN/saltmarket_Monopoly_bot`. The owner created the Vercel project by hand (root `web`)
  and turned Deployment Protection off.

## What changed
- `web/vercel.json`: kept COOP/COEP and the long cache on `/runtime/app.*.zip` and `/pyodide/*`.
  Added `X-Content-Type-Options: nosniff` and an immutable cache on `/assets/*`. No SPA rewrites:
  the app has one page and no router.
- `web/scripts/build-runtime.mjs`: `npm run runtime:assets` now tries `python3`, `python`, then
  `py`. With no Python it uses the committed bundle and prints a warning.
- **Decision: committed bundle plus robust build step.** `web/public/runtime/` is no longer
  gitignored (about 3 MB). The committed zip is only a fallback. On Windows git converts line
  endings, so its hash can differ from a Linux build; rerun `npm run runtime:assets` and commit
  after engine, data or model changes.
- `.github/workflows/ci.yml`: new `web` job (typecheck, lint, `vitest run`, `npm run build`)
  beside the existing ruff and `pytest -m "not slow"` job. No agent-browser in CI.
- Stale repo name `saltmarket-ai` replaced by `saltmarket_Monopoly_bot` in `CLAUDE.md`,
  `docs/web/PLAN.md`, `docs/web/handoff/plan.md`, `HANDOFF.md`, `web/src/hud/facts.ts`.

## Verified
- Local: `tsc`, lint, `npm run build` clean; Vitest 115 passed, 3 skipped. `npm run preview`
  returns COOP/COEP; the other Vercel headers only apply on Vercel.
- Live (agent-browser, https://saltmarket.vercel.app/): `crossOriginIsolated` is `true`; console
  shows one warning (`THREE.Clock: This module has been deprecated`) and no errors. Start game
  at 2 players against PPO loaded the Pyodide worker from this host, showed a buy decision, and
  played on through a PPO turn and an auction (cash and positions changed).
- Not checked live: a full game to the end, mobile layout, the Vercel-only headers via curl.

## Left for later
- `THREE.Clock` deprecation warning comes from a dependency.
- Large main chunk warning (over 500 kB) from Vite; no code splitting yet.
- `ruff` was not on PATH in this shell; CI runs it.
