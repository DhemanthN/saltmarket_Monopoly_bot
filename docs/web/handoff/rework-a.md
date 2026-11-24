# Rework A: HUD, UI and store slice

Branch `rework-a`. A second tab ("world") fixed the 3D items (F1, F4-F7, F21, F23, F24, F26-F30) and is documented separately.

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
