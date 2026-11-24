# Final QA check

Date: 2026-11-24. Target: https://saltmarket.vercel.app/ after the visual upgrade (main at `334d53f`). Nothing was fixed in this task.

Found by two subagents: `qa-browser` (smoke flows) and `design-critic` (visual review). Viewports: desktop 1440x900 and phone 390x844. Screenshots are not committed.

Severity: **blocks play** (a player cannot continue or cannot read a control) or **looks wrong** (visible defect or misleading behaviour).

## Issues, ranked

### 1. Blocks play: Pass button invisible at night
- Viewport: phone 390x844 (desktop shows a cream strip under Pass).
- Screen: auction or buy panel after turn 16 (night).
- Repro: start 2p vs PPO, keep playing until turn 16 or later, open any auction or buy panel. Pass is cream text on a cream bar. The primary "Bid" button blends into the bar.
- Cause: `.actions { background: var(--paper) }` does not change at night. `--paper` is missing from the `[data-mood="night"]` block.
- Files: `web/src/hud/decisions/DecisionPanel.module.css:399-404`, `web/src/styles/tokens.css:114`. Use `var(--surface)` for the bar.

### 2. Looks wrong: auction offers bids that cannot win
- Viewport: both.
- Screen: auction.
- Repro: Wave (PPO) bids the top chip (for example 360 on a list price of 180). The panel still shows chips 1-7 and makes "Bid 45" the primary.
- Cause: `liveBids` falls back to every chip when none beats the high bid.
- File: `web/src/hud/layout.ts:66-69`. Show only Pass plus a line such as "Wave leads at 360, the top bid".

### 3. Looks wrong: Raise-cash panel looks stalled on Enter
- Viewport: desktop 1440x900.
- Screen: raise-cash panel (cash below the amount owed).
- Repro: buy Malachite Rise so cash is short. The highlighted option ("Mortgage Northwind Ferry") sits outside the numbered list and has no Enter hint. Enter did nothing in 80 presses.
- File: the raise-cash decision panel under `web/src/hud/decisions/` (grep "Raise cash").

### 4. Looks wrong: phone in-game HUD overlaps and the scene is small
- Viewport: phone 390x844, 2p and 4p.
- Screen: in-game.
- Repro: start any game. The "top choices" lantern chip sits on the bottom edge of the ledger bar. The Menu button covers the place-name label (top right). The 3D scene gets about 420 px of the height.
- Files: `web/src/hud/Lantern.module.css`, `web/src/hud/HudView.tsx` and its CSS module.

### 5. Looks wrong: phone start screen hides "Start game"
- Viewport: phone 390x844.
- Screen: start screen.
- Repro: open the site. "Start game" has its top at 817 px of 844, below the fold in a scrolling panel. The ship takes about 40% of the height. "How to play" appears twice (legend over the mode list and a link at the bottom).
- File: `web/src/screens/StartScreen.tsx:81`. Rename the legend to "Opponent" and pin Start in a sticky footer.

### 6. Looks wrong: turn counter repeated and reads "Turn 0"
- Viewport: both.
- Screen: in-game top readout.
- Repro: the mono readout says "Turn 0 Round 1 Dawn Cash 1,400" while the ledger says "Day 1, dawn · turn 0". Cash repeats. The navy glass plate clashes with the paper HUD.
- File: `web/src/hud/Chrome.tsx` near line 92. Drop the cash, start counting at 1, use paper or brass.

### 7. Looks wrong: far space label overlaps the top readout
- Viewport: desktop 1440x900.
- Screen: in-game.
- Repro: a far label such as "Regent's Landing 360" can overlap the turn/round/cash readout.
- Files: space labels under `web/src/world/`.

### 8. Looks wrong: loading screen and display font versus the docs
- Viewport: both.
- Screen: loading.
- Repro: loading is the ship plus "Laying the reef 0%", not the atoll being built (ANTI_SLOP #11). The display font is Cinzel, but `docs/web/DESIGN.md` specifies Fraunces.
- Files: `web/src/styles/fonts.css`, `web/src/styles/tokens.css`, or update `docs/web/DESIGN.md`.

## Passed flows

- 1440x900: load, 2p vs PPO, buy, auction, mortgage and Brig panels, Menu, Calm, Low tier, Leave game, 4p table.
- 390x844: load, 2p start, buy, auction, Leave game, 4p start.
- Game over and "Replay, same seed" reached in Watch bots (3p, turn 272). Replay restarted cleanly from turn 0.
- Not reached: game over in a human 2p game (played to turn 42).
- There is no day/night toggle in production. Night follows the turn count (`web/src/world/sun.ts`).
- Console: only a `THREE.Clock` deprecation warning. No errors.

## Perf (`?perf=1`, headless Chrome)

| Viewport | Tier | DPR | fps | Draw calls | Triangles |
|---|---|---|---|---|---|
| 1440x900, 2p | high | 1 | 60 | 55 | 27.2k |
| 390x844, 2p | low | 1 | 11 on two samples, 60 on a rerun | 29 | 17.5k |

The 11 fps reading may be software rendering or a startup transient. It was not reproduced on a second phone run. All draw-call counts are under the 150 budget.

## Summary

1. One issue blocks play: Pass is unreadable at night (fix `--paper` in the night tokens).
2. Auction chips can offer bids that cannot win, and the raise-cash panel looks stalled on Enter.
3. The phone layout needs work: HUD overlaps, small scene, and Start below the fold.
4. Perf is within budget (55 draw calls on desktop, 29 on phone); one unreproduced 11 fps phone sample.
5. Replay, Menu, Calm, 4p and the console are clean apart from a deprecation warning.
