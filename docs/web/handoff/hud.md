# Handoff: hud

Branch: `hud` · Date: 2026-11-23 · Status: done (design-critic run 3 times; remaining items below are minor)

## What changed
- `web/src/hud/`: reducer (`state.ts`), panel layout model (`layout.ts`), facts and results text (`facts.ts`, `resultsFacts.ts`), decision panels (`decisions/DecisionPanel.tsx`), thought lanterns (`Lantern.tsx`), ledger rail (`LedgerRail.tsx`), coach marks (`CoachMarks.tsx`), game-over screen (`GameOver.tsx`), keyboard handling (`useDecisionKeys.ts`).
- `web/src/screens/HudPage.tsx`: dev page that replays a recorded fixture through the HUD and opens any decision kind. Not in production builds.
- Design fixes: mobile ledger strip and bottom sheet with sticky action footer, coach marks anchored to their targets, auction bid ladder and one-row chips, bids above cash hidden (`panelModel(decision, cash)`), trade group badges and swatches (`hud/groups.ts`), decision panel docked bottom-left, panel-enter and rent-coin motion (crossfade under reduced motion), amounts on primary buttons, list rows numbered from 1, ledger qualifiers moved to the net worth line.
- Final polish commit: tighter decision panel layout, lantern and coach mark styling, event feed limit cut from 8 to 5, and the dev page fixture glob now filters out `index.json` instead of using the `!(index)` pattern.
- No engine or contract files changed.

## Decisions made (and why)
- Feed limit 5: the ledger rail stays readable at laptop height.
- Dev page filters `index.json` in code, because the extglob pattern is not reliable across Vite versions.

## How to verify
- Commands: `cd web; npx tsc --noEmit; npm run lint; npx vitest run; npm run build`
- What you should see: no type or lint errors, 76 tests passing in 8 files, build succeeds (one chunk-size warning, not new).
- Visual: `npm run dev`, open the HUD dev page, step through each decision kind.

## Tests
- Added: `state.test.ts`, `layout.test.ts`, `facts.test.ts` (reducer, layout model, facts), `groups.test.ts` (group completion), plus a cash-limited bids case in `layout.test.ts`. No render or pixel tests, per the web testing rules.
- Results: 76 passed (Vitest). Python suite not run: no Python files changed.

## Left for later / known issues
- `design-critic` ran three times. Round 1 gave 8 findings and round 2 gave 5; all of those are fixed. Round 3 passed every check and found 3 layout problems caused by the fixes, which were then fixed without a fourth pass: mobile rent ladder back to 3 columns, mobile bid ladder shrunk to one row (so the chips stay above the fold), build caption renamed "More choices". Not re-verified by screenshot.
- Open, minor:
  - The coach highlight ring keeps its old size when the seat count changes without a resize (dev page only).
  - The mobile sticky footer's top rule is inset about 8 px instead of full width.
  - Game over on mobile wraps seat qualifiers onto 3 lines (existed before).
  - A short-cash Buy button keeps ink styling; only the "Cash after buying" figure uses the danger colour.
  - Night mode on the dev page puts dark panels over a static daylit silhouette; the real world switches mood together with the panels.
  - Coach tips are decided per step from what is on screen; a tip whose target never appears is skipped.
- `perf-auditor` not run: no `web/src/world` changes.
- Build warns about a chunk over 500 kB; code-splitting belongs to the deploy task.

## What the next task needs to know
- The HUD takes events from the `GameSession` contract through `reduceHud`; mount `HudView` over the 3D scene and feed it the same event stream.
- Every number the HUD shows must come from `results/` with its table size; `resultsFacts.ts` is the single place that does this.
