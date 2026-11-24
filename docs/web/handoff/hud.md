# Handoff: hud

Branch: `hud` · Date: 2026-11-23 · Status: done (design-critic review pending, see below)

## What changed
- `web/src/hud/`: reducer (`state.ts`), panel layout model (`layout.ts`), facts and results text (`facts.ts`, `resultsFacts.ts`), decision panels (`decisions/DecisionPanel.tsx`), thought lanterns (`Lantern.tsx`), ledger rail (`LedgerRail.tsx`), coach marks (`CoachMarks.tsx`), game-over screen (`GameOver.tsx`), keyboard handling (`useDecisionKeys.ts`).
- `web/src/screens/HudPage.tsx`: dev page that replays a recorded fixture through the HUD and opens any decision kind. Not in production builds.
- Final polish commit: tighter decision panel layout, lantern and coach mark styling, event feed limit cut from 8 to 5, and the dev page fixture glob now filters out `index.json` instead of using the `!(index)` pattern.
- No engine or contract files changed.

## Decisions made (and why)
- Feed limit 5: the ledger rail stays readable at laptop height.
- Dev page filters `index.json` in code, because the extglob pattern is not reliable across Vite versions.

## How to verify
- Commands: `cd web; npx tsc --noEmit; npm run lint; npx vitest run; npm run build`
- What you should see: no type or lint errors, 72 tests passing in 7 files, build succeeds (one chunk-size warning, not new).
- Visual: `npm run dev`, open the HUD dev page, step through each decision kind.

## Tests
- Added: `state.test.ts`, `layout.test.ts`, `facts.test.ts` (reducer, layout model, facts). No render or pixel tests, per the web testing rules.
- Results: 72 passed (Vitest). Python suite not run: no Python files changed.

## Left for later / known issues
- `design-critic` was launched on the HUD screens but its report had not arrived when this was written. Apply its findings before calling the UI final.
- `perf-auditor` not run: no `web/src/world` changes.
- Build warns about a chunk over 500 kB; code-splitting belongs to the deploy task.

## What the next task needs to know
- The HUD takes events from the `GameSession` contract through `reduceHud`; mount `HudView` over the 3D scene and feed it the same event stream.
- Every number the HUD shows must come from `results/` with its table size; `resultsFacts.ts` is the single place that does this.
