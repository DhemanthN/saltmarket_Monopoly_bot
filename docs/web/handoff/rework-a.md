# Rework A: both slices (HUD/UI/store and world)

Branch `rework-a`. Two slices. Part 1 is HUD, UI and store (main tab). Part 2 is world, runtime and bundle (helper tab "world"); its full notes are in `rework-a-world.md`. `GameScreen` now uses `useQualityChoice()` (quality persists across reloads) and passes `paused` to `WorldScene` while the error panel is open.

## Part 1: HUD, UI and store

## What changed

| Item | Change |
|---|---|
| F2 | On phones the coach card sits just above the decision sheet and drops its counter line, so it no longer covers Menu, Chart view or the lantern chip. |
| F3 | When the person is bankrupt a banner says so and offers "Fast-forward to the result". `store.fastForward` drops the pause before bot moves. |
| F8 | Ledger rows show cash only. Net worth sits behind "Show net worth" (default closed). The feed holds 3 lines. |
| F9 | `store/tradeOffers.ts`: the store passes quietly on a trade offer unless the set of buyable groups is new or 12 turns passed. Declines now name the seat: "Star declined your offer". |
| F10 | Brig, build and raise-cash panels put the buttons before the row list. Primary hover only applies where hover exists, so touch no longer leaves it grey. |
| F11 | Auction chips at or under the high bid are dropped (`liveBids`), so the default bid beats the leader. Copy rewritten. |
| F12 | Action buttons stay in view when the panel scrolls. Rent ladder is two columns on phones. Panel fits short screens. |
| F13 | `ui/useFocusTrap.ts` traps Tab in dialogs and on game over. Escape on game over folds it into a result bar. |
| F14 | "Replay, same seed" starts a new game with the same config (`store.replay`). "Back to the start" is separate. Bot-only tables no longer show the win-rate line. Seat names use short names and "(out)". Scrim is lighter. |
| F15 | Start panel is capped at 52% height on phones; intro and seat list are hidden there. |
| F16 | Panel and tip titles are Plex semibold. Deed name is smaller than the title. |
| F18 | Choosing 3 or 4 players with DQN switches to PPO and says why. |
| F19 | Opponents: PPO, DQN, Expert bot, Balanced bot, Always-buy bot. Not every engine strategy. |
| F20 | Size radios and the opponent select are 44 px tall. |
| F22 | Raw error text moved into a collapsed "Technical details". |
| F25 | Ledger caption "Day 3, dusk · turn 62". Night stays counted in turns (owner answer). |
| F31 | "Pass to auction", "Other options", "Read the full results", plain lantern subtitle, short seat names in the feed, 12 px minimum for net worth. |
| F32 | Reduced-motion variants for coach marks and toasts. |

## Not done

- F9 counter offer: the engine has no counter action. Offers are throttled instead.
- F10 "tries left" and "use card": the decision carries no tries count, so none is shown. Use card is still untested.
- F11 camera cut to the market square: world code.
- F14 winner orbit and flags: task 8.
- F22 loading signboard: world code.
- F32 theme and sound toggles: not built.

## How to verify

`cd web; npx tsc --noEmit; npx eslint .; npx vitest run` (138 pass). `python -m pytest -m smoke` (426 pass). Live check ran on a local dev server (port 5217, now stopped): start screen, 2p and 4p games, buy panel with 2-column ladder, bankrupt banner, game-over dialog with Tab trap, Escape fold and replay (seed stayed 5). Phone check used a 390 px iframe: start panel and coach card placement. The iframe froze before the game-over screen, so game over was checked at desktop width only.

## Notes

`npm run dev` runs `fetch-pyodide` first. Running `npx vite` alone leaves the engine stuck at 0%.

## Part 2: world slice (summary of `rework-a-world.md`)

| Item | Change |
|---|---|
| F1 | `world/chartFit.ts` fits the ring into the open frame above the sheet. Tested at 390x844 in a unit test. |
| F4 | Day, dusk, night and dawn ease in turns (24 per day). `WorldScene` sets `data-mood`, so the HUD night panel applies. Windows and lamps glow at night. |
| F5 | `TierGovernor` replaces the drei monitor. Desktop starts on High, phones on Medium, Auto Low probes to climb back. Reduced motion no longer forces Low. |
| F6, F7 | Signboards hide when overlapping, avoid the ledger rail, use ledger names. |
| F21 | `beforeunload` warning during a game. Quality choice persists. |
| F23 | Console warnings removed, except the upstream `THREE.Clock` one, which is filtered. |
| F24 | Open-centre sun emblem and a distinct piece shape per seat. |
| F26 | Main chunk 34 kB (was 1.23 MB). `three` chunk 1.15 MB loads at Start. |
| F27 | `?perf=1` enables `window.__saltmarketPerf` with texture and geometry counts. |
| F28 | Weights ship as separate files and only the chosen opponent's loads. A PPO 2p game downloads about 1.2 MB of runtime, not 3.4 MB. |
| F29 | Not reproduced in code. Needs the perf-auditor on Low. |
| F30 | Per-frame allocations removed and geometries disposed on unmount. |

World slice skipped: stars, moon and bloom (task 8). Night stays turn-based by owner answer.

## Live checks not done

- Phone 390x844: the browser tool refused the resize, and an iframe froze before game over. Phone game over, bankrupt banner and sheet layout are unchecked. Phone chart fit is covered by a unit test only.
- Phone landscape 844x390 (F12): not checked.
- 4x CPU throttle, real-phone fps, perf-auditor on Low (F5, F29).
- Jail "use card" (F10) and a build decision: not reached.
- Live Vercel URL: not checked until main deploys.
