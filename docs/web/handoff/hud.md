# Handoff: hud

Branch: `hud` · Date: 2026-11-23 · Status: done, design-critic verdict FIX (open items below)

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
- `design-critic` verdict: FIX. ANTI_SLOP checklist passes; DESIGN.md violations remain (screenshots in `.pane/scratch/critic/`):
  1. Mobile (390x844): decision panel (y 360-828) covers the ledger (y 674). Needs a bottom sheet of about 50vh and a one-line cash strip pinned at the top.
  2. Coach marks are not anchored to their targets (piece, panel edge, lantern button). Tip 3 refers to a lantern that does not exist in `bots_3p`, and on mobile the tip covers the lantern.
  3. Auction: 5 chips wrapped 4+1 instead of 7 in a row, no live bid ladder with seat emblems, and chips above the player's cash are still offered (may be a sample-decision mismatch, check the real flow).
  4. Trade panels: no "completes a group" badge or district swatch, lowercase group chip ("kelp"), "Offer 60 For ..." capital F.
  5. No motion: no 240 ms panel enter, no travelling rent coin.
  6. Desktop decision panel covers the ring centre and the signboard of the space being decided. Dock bottom-left, width 400.
  7. Primary buttons for build, raise cash and liquidate show no amount. Buy with negative cash after should show danger colour and "(raise N first)". Number list rows from 1.
  8. Night: dark panels over a daylit world, lantern bar track dark on dark, lantern heading in Plex not Fraunces, "Star (always buy)" and "You (bankrupt)" wrap in the 340 px ledger.
- Keep: the Buy deed card, one clear primary per panel, the game-over honesty line.
- `perf-auditor` not run: no `web/src/world` changes.
- Build warns about a chunk over 500 kB; code-splitting belongs to the deploy task.

## What the next task needs to know
- The HUD takes events from the `GameSession` contract through `reduceHud`; mount `HudView` over the 3D scene and feed it the same event stream.
- Every number the HUD shows must come from `results/` with its table size; `resultsFacts.ts` is the single place that does this.
