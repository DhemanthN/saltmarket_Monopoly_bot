# QA fix list (task 7)

Date: 2026-11-24. Target: https://saltmarket.vercel.app/ (branch `qa`, main at `b35b1bc`). Nothing was fixed in this task.

Found by three subagents run one after another: `qa-browser` (QB), `perf-auditor` (PA), `design-critic` (DC). Viewports: phone 390x844 and desktop 1440x900, plus one 844x390 landscape check. Screenshots are not committed; they were kept in the session scratchpad (`qa-shots/` from QB, `design-shots/` from DC).

Severity: **blocks play** (a player cannot continue or cannot see the board), **looks wrong** (visible defect or misleading behaviour), **polish** (works, but basic or rough). All `web/src/...` paths below are written relative to `web/`, so `world/CameraRig.tsx` means `web/src/world/CameraRig.tsx`.

## What was and was not covered

| Flow | Result |
|---|---|
| Full game to the end, 2p vs PPO, desktop | Pass. 57 turns, 91 s. Win-rate line: 82.0% of 40,000 games at 2 players against the 40 bots (CI 81.6-82.4) |
| Full game to the end, 4p vs PPO plus 2 bots, phone | Pass, but 665 turns and about 25 min after the tester went bankrupt early (F3). 35.2% of 20,000 games at 4 players |
| DQN, 2p only | Pass. Game over after 59 turns, 78.3% of 40,000 games at 2 players. Disabled at 3-4p (F18) |
| Bot opponents | Partial. Only one bot type (`expert`) is offered (F19). Full 2p game finished at 77 turns |
| Trade screen | Reached. Accept works. The AI declined every other offer. No counter exists (F9) |
| Jail screen | Reached about 25 times. Pay fine and roll for doubles work. "Use card" never appeared, so it is **untested** (F10) |
| Coach tips 1, 2, 3 | Pass. Next, Next, Got it. Skip works. Stored in `localStorage` key `saltmarket.coach.done` |
| Game over and replay | Dialog works. "Play again" returns to the start screen and there is no real replay (F14) |
| Menu and How to play dialogs | Open, Escape and Leave-game confirm work on both viewports. Focus trap fails (F13) |
| Error and retry | Pass. Blocking `runtime/app.*` shows the error panel and Retry works (F22) |
| Day and night | Night only happens through the 24-turn sun cycle. No toggle. The HUD never switches mood (F4) |
| Not measured | 4x CPU throttle on phone, texture and geometry counts, 5-minute memory run (ran 2.5 min), a build or upgrade decision (never reached in about 120 turns), jail "use card", AI trade counter |

## Ranked fix list

### Blocks play

**F1. Chart view crops the atoll on phone.** Found by QB (B3) and DC (D2).
- Viewport: 390x844. Screen: chart view. Day and night.
- Repro: 1. Start any game. 2. Tap "Chart view".
- Actual: the ring is cropped left and right, and the bottom sheet hides the lower half and the pieces. Street view offsets the camera for the sheet. Chart view does not.
- Fix target: fit the whole ring into the area above the sheet (`bottomInset`).
- Files: `world/CameraRig.tsx`, `world/WorldScene.tsx`, `hud/layout.ts`.

**F2. Coach tips cover the controls they explain on phone.** Found by QB (B2) and DC (D1). DC rated this blocks play and QB rated it looks wrong. Skip tips always works, so it sits here only because every new phone player meets it.
- Viewport: 390x844. Screen: street view, first turns.
- Repro: 1. Start a game. 2. Read tip 1 ("You and the road"): it covers Menu, Chart view and the lantern chip. 3. Tip 3 covers Chart view ("rt view" visible).
- Files: `hud/CoachMarks.tsx` (`place()`), `hud/CoachMarks.module.css`, `hud/layout.ts`.

**F3. A bankrupt player has no way out of a long game.** Found by QB (B14).
- Viewport: both. Screen: any game with 3 or more players.
- Repro: 1. Start a 4p game. 2. Go bankrupt early. 3. The game keeps running to the end: 665 turns, about 25 minutes. There is no "you are out" message, no fast-forward and no skip to the result.
- Files: `store/gameStore.ts`, `hud/HudView.tsx`, `hud/GameOver.tsx`.
- Note: DC saw a phone frame with "0 You / 0 Anchor" and no game-over panel (D14, `phone-stall-1.png`). QB's long game is the likely cause, but this was not confirmed as a stall.

### Looks wrong

**F4. Night never looks like night, and the HUD ignores mood.** Found by DC (D3). Wow gap 1.
- Viewport: both. Screens: street and chart. Night.
- Repro: play to turn 18 of a 24-turn cycle. The sky is flat slate `#637B95` (DESIGN says `#16232B`) with a hard dark band at the horizon. No window or lantern glow. The HUD stays on day paper because `data-mood` is never set outside dev pages.
- At 4 players night passes in a few bot turns, so it flickers like a glitch. Count rounds, not seat turns.
- Files: `world/sun.ts`, `world/Sky.tsx`, `world/palette.ts` (night `ink` maps to mid-grey and awnings lose contrast), `screens/GameScreen.tsx` (should set `document.documentElement.dataset.mood`), `styles/tokens.css` (`[data-mood="night"]` exists but is unused).

**F5. Auto quality drops to Low on a healthy machine and never recovers.** Found by PA (P1) and DC.
- Repro: open on the phone emulation and leave quality on Auto. Street runs at 55 fps with p99 34 ms, then chart view draws 0 calls (Low). Medium and High both held 60 fps. In Low, `frameloop="demand"` starves `PerformanceMonitor` of frames, so it cannot step back up.
- Any richer effect only shows on High, so this gates the whole polish rework.
- Fix target: keep the monitor fed while in Low, raise the decline threshold (street is about 30 draws), and start on High on desktop GPUs.
- Files: `world/WorldScene.tsx` (lines 124, 125, 150-157), `world/quality.ts`. Line 124 also forces Low when reduced motion is on, which removes shadows.

**F6. Signboards overlap and slide under the ledger.** Found by QB (B7) and DC (D4).
- Viewport: desktop. Screen: street view. Day and night.
- Repro: play until owned lots are close together. "Malachite Rise Wave owns" sits over "...ine Cove Sun owns", and "Northwind Ferry" covers "Sugarkelp Bank". "The Br" and "Bladderwrack F" are cut off by the ledger rail.
- Files: `world/Signboards.tsx` (`STAGGER_PX`, `SAFE_X`), `world/Signboards.module.css`, `ui/Signboard.tsx`.

**F7. Signboards use different seat names than the ledger, and empty posts look unfinished.** Found by DC (D5).
- Signs say "Sun owns" and "Wave owns", while the ledger says "You". Every non-buyable space has a blank white post.
- Files: `world/Signboards.tsx:21-27`, `world/geometry.ts`.

**F8. Ledger rail and feed cover about 35% of the world at 4 players.** Found by DC (D6).
- Viewport: desktop. Screens: street and chart.
- Repro: start a 4p game. The rail plus feed is about 340x520 px at the top right, and the decision panel covers the bottom left.
- Fix target: merge net-worth sub-rows into the main row, cap the feed at 3 lines, make it collapsible. Older feed lines fade to about 30% opacity, which fails contrast.
- Files: `hud/LedgerRail.tsx`, `hud/LedgerRail.module.css`.

**F9. "Offer a trade" appears every turn and the AI never counters.** Found by QB (B12) and DC (D7).
- Viewport: both.
- Repro: own one lot of a group. The offer panel opens on each of your turns (39 times in one 4p game). Every decline writes "A trade was declined" with no seat named. No counter option exists.
- Fix target: offer on demand (a ledger button) or once per new group opportunity, and name the seat in the feed.
- Files: `hud/decisions/DecisionPanel.tsx`, `hud/state.ts`.

**F10. Jail screen is thin and its primary button looks disabled.** Found by QB (B13) and DC (D11).
- Repro: land in The Brig. "More choices" and the "Pay the fine 60" row come before the primary in reading order. On phone, "Roll for doubles" renders grey-slate like a disabled button. The same happens to "Accept" on a trade offer. No text says how many tries are left. The "use card" option never appeared in about 25 visits, so it is untested. The jail has no visual change in the world.
- Files: `hud/decisions/DecisionPanel.tsx:226`, `hud/decisions/DecisionPanel.module.css`, `ui/Button.module.css` (check hover and focus colours).

**F11. Auction panel is confusing.** Found by DC (D8).
- Repro: let the opponent bid first. The ladder shows Wave at 135, yet the default chip and the primary button say "Bid 22". Chips under the high bid look live. "List price 90. Bids are shares of it." is unclear. DESIGN asks for the auction to cut to the market square, but the camera stays on street view.
- Files: `hud/decisions/DecisionPanel.tsx` (around line 198), `world/CameraRig.tsx`.

**F12. Buy panel and landscape layout on phone.** Found by QB (B4) and DC (D10).
- 390x844: the bottom sheet takes 50% of the height and the rent ladder is cut at "2 depots" with a hidden scroll.
- 844x390: Buy and Decline sit at y=486 to 582, below the 390 px viewport, so the panel scrolls inside itself.
- Files: `hud/decisions/DecisionPanel.module.css`, `hud/layout.ts`.

**F13. Modals do not trap focus.** Found by QB (B1).
- Viewport: both. Repro: open Menu or How to play and press Tab 3 to 11 times. Focus leaves for the page behind. Game over has no Escape handler and no trap, and Tab reaches the Menu button behind it.
- Files: `ui/Dialog.tsx`, `ui/useModalKeys.ts`, `hud/GameOver.tsx`.

**F14. Game over: wrong label, wrong copy, wasted scene.** Found by QB (B5, B9) and DC (D13).
- "Play again" goes to the start screen. There is no replay and no separate "back to menu" (`GameScreen.tsx`: `onPlayAgain={leave}`).
- Bot games say "No measured win rate exists for this table size yet", which misleads because bots have no win rate at any size.
- Phone: seat names wrap onto three lines ("Star (always / buy) / (bankrupt)"). The scene is washed beige behind the modal, so the winner's world is not shown.
- Files: `hud/GameOver.tsx`, `hud/GameOver.module.css`, `screens/GameScreen.tsx`.

**F15. Start screen: panel buries the world on phone, atoll is placeholder boxes.** Found by QB (B6) and DC (D15).
- At 390 wide the panel is flush to the bottom and covers about 70% of the atoll, and the "Home Quay" sign is clipped. On desktop the start atoll is flat extruded district boxes, not the real silhouettes used in game, and the sign floats mid-lagoon.
- Files: `screens/StartScreen.module.css`, `screens/StartScreen.tsx`, `world/AtollSilhouette.tsx`.

**F16. Panel titles and deed names compete.** Found by DC (D9).
- "Buy or pass" (20 px Fraunces) is smaller than the deed name under it. DESIGN says h4 is Plex semibold.
- Files: `hud/decisions/DecisionPanel.module.css:28`, `hud/CoachMarks.module.css:35`.

**F17. Chart view has too little information.** Found by DC (D17) and QB.
- Viewport: desktop. Buildings are about 15 px, with no readable levels, lot names or owner pips. Concentric ink rings and a compass rose that does not track the camera carry no information (anti-slop item 8). In street view the same rings show as stray dark lines across the sea.
- Files: `world/Signboards.tsx` (`street` prop), the chart ring and compass code in `world/`.

### Polish

**F18. DQN silently reverts to PPO at 3 or more players.** Found by QB (B10). Choose DQN, then click 3 players: the opponent switches to PPO with no explanation. Files: `screens/StartScreen.tsx`, `screens/startConfig.ts`.

**F19. Only one bot type is selectable.** Found by QB (B11). "Scripted bot" is always `expert` in seat 1. Fillers are `always_buy` and `balanced`. The start screen names none of them. Files: `screens/startConfig.ts`, `screens/StartScreen.tsx`.

**F20. Start-screen controls are under 44 px on phone.** Found by QB (B8). Table-size radios are 37 px and the opponent select is 40 px. File: `screens/StartScreen.module.css` (lines 58, 101).

**F21. Reload and Back lose the game with no warning.** Found by QB (B15). Reload returns to the start screen, Back leaves the site, and the quality setting resets to Auto. Files: `store/gameStore.ts`, `App.tsx`.

**F22. Error panel shows raw text and cuts through the loading signboard.** Found by QB (B17). It shows "TypeError: Failed to fetch" to the player on desktop. File: `screens/RuntimeTrouble.tsx`. Loading shows "Laying the reef 0%" over a static silhouette (DC, anti-slop item 11). File: `world/AtollSilhouette.tsx`.

**F23. Console warnings.** Found by QB (B16). `THREE.Clock deprecated`, `BufferGeometry.toNonIndexed(): already non-indexed` (repeated) and `PCFSoftShadowMap has been removed`. Files: `world/` (shadow setup, geometry building). No errors.

**F24. Player flag emblem reads as an ink splat, and pieces are identical cones.** Found by DC (D12). Files: `world/emblems.ts:53`, `world/Pieces.tsx`.

**F25. No turn, day or round indicator.** Found by DC (D16). The day/night cycle and game length have no visible build-up. File: `hud/LedgerRail.tsx` (add a "Day 3 - dusk" caption).

**F26. Main chunk is 1.23 MB decoded (350 kB transferred).** Found by PA (P2). Over the 500 kB rule. Only `ChartTiltShift` (39 kB) is lazy. Files: `App.tsx`, `vite.config.ts` (`manualChunks`), `world/WorldScene.tsx`.

**F27. No perf probe in production and no texture or geometry counts.** Found by PA (P3). `__saltmarketPerf` exists only with `DEV_PERF`, and `PerfSnapshot` lacks `gl.info.memory`. Add `?perf=1`. Files: `world/quality.ts` (38-54), `world/WorldScene.tsx` (85-119).

**F28. Cold download is about 10 MB.** Found by PA (P4). The runtime zip (3.4 MB) is stored uncompressed and holds three 1.1 MB `.npz` models. The pyodide wasm is 3.58 MB and the stdlib zip is 2.55 MB. Load only the chosen opponent's model, or compress. Files: `public/runtime/app.*.zip`, `runtime/engine.worker.ts` (69-83). Timings: atoll visible at about 1.2 s and first decision at about 7.1 s cold (QB), 2.6 s from the Start click (PA).

**F29. Low tier idles at 45 fps rAF with 0 draws.** Found by PA (P5). May be a headless artefact. Check `invalidate()` and the `Signboards` `useFrame` (line 63) in demand mode.

**F30. Per-frame garbage and disposal.** Found by PA (static review). `new Color` or `new Vector3` in `CoinCarts` (line 50), `Signboards` (line 56) and `Pieces` (line 28). `dispose()` appears only in `Sky.tsx`, so check unmount of the other geometries and materials.

**F31. Copy and typography.** Found by DC (section D).
- "Decline and send it to auction" should be "Pass to auction" (DESIGN wording). "Read RESULTS.md" exposes a filename. "Bids are shares of it" is unclear. "A trade was declined" names nobody. "More choices" is a label, not copy. The DQN lantern subtitle "Q-value of each action, last decision" is jargon. Seat labels vary ("Wave (expert)", "Wave", "Wave owns", "Wave seat").
- The net-worth sub-row is about 11 to 12 px, below the 12 px minimum.
- Files: `hud/decisions/DecisionPanel.tsx`, `hud/GameOver.tsx`, `hud/facts.ts`, `screens/StartScreen.tsx`, `hud/LedgerRail.module.css`.

**F32. Missing controls and motion gaps.** Found by QB and DC.
- No theme toggle and no sound control, on the start screen or in Menu.
- The coach mark and toast have no `prefers-reduced-motion` variant (`hud/CoachMarks.module.css`, `ui/Toast.module.css`). The Menu reduced-motion toggle also forces Low tier.
- Not confirmed: whether the lantern chip opens empty before the agent's first decision (`hud/Lantern.tsx`).
- Every panel uses the same `panel-in` fade (anti-slop item 9, borderline).

## Anti-slop checklist (DC)

Fail: item 8 (decorative rings and compass rose) and item 11 (loading shows a percent over a static outline, and the start atoll is boxes). Borderline: item 6 (every HUD box looks alike) and item 9 (one fade for everything). Pass: items 1 to 5, 7, 10 and 12.

## Performance budget (PA)

| Metric | Budget | Desktop 1440x900 | Phone 390x844 (DPR 3 emulation) | Result |
|---|---|---|---|---|
| fps, High and Medium | 60 | 60.0-60.1, p99 17.8 ms | rAF 119.6 (120 Hz panel), p99 8.5 ms | pass |
| fps, Auto street | 60 | 60 | 55.3, p99 33.9 ms, then Low | marginal (F5) |
| Draw calls, street | <150 | 32 (High, Medium), 26 mid-game | 29 | pass |
| Draw calls, chart | <150 | 53 (Medium), 54 plus 2 post passes (High) | 33-34 | pass |
| DPR | <=2 | 1 | Medium 1.5, High 2, Low 1 | pass |
| Shadow refresh | on board change only | 0 shadow passes in static street. Chart High has 2 binds per frame, from the composer | same | pass |
| Idle draws (start screen, game over) | none | 0 | 0 | pass |
| JS heap | none stated | 8-14 MB, flat over 210 s | 11-12.5 MB | pass |
| Long tasks | none | 0 | 0 | pass |
| Main chunk | <500 kB | 1,231,889 B decoded, 349,687 B transferred | same | fail (F26) |

Method limits: the production build hides `renderer.info`, so draw calls were counted by wrapping WebGL draw calls. The GPU was the Radeon 890M in headless Chrome. A 4x CPU throttle was not possible, so phone fps is not throttled-CPU data. Textures and geometries were not measured.

**Headroom for the rework.** Street uses 26-32 of 150 draw calls and chart uses 53-54, leaving about 95-120. The 890M holds a flat 16.7 ms at DPR 1 on High with shadows and tilt-shift on. A water shader and particles should fit at DPR 1 to 1.5. The real risk is DPR 2 plus the full-screen composer on a real mid-range phone, which was not tested. Keep new effects behind `settings.effects` (High only), keep Low as the fallback, and fix F5 first or the new visuals will rarely show.

## Wow gaps (ranked)

1. **Night and time of day (M).** Now: flat slate sky, no emissives, HUD unchanged. Add a real night palette, emissive windows and lanterns through the second palette texture, amber roof glow at dusk, a moon disc, stars in the dome shader, a warm-to-cool sky gradient, a slower cycle counted in rounds, and the HUD `night-panel`. Perf: free (texture swap and dome shader). Bloom on lanterns is High only. Depends on F4 and F5.
2. **Water (M).** Now: flat lagoon and ocean discs with ink rings. Add a scrolling normal or vertex shader, foam bands at the sand edge, lighter shallows near the ring, and a static normal map on Medium. DESIGN already specifies this, but `quality.ts` `effects` gates only tilt-shift. Perf: 0 to 2 draws.
3. **Life: boats, gulls, smoke (M).** Now: nothing moves. Add 3 to 5 instanced sailboats on loops outside the ring, 6 to 10 gulls, chimney smoke from cinder foundries, and a quay crane that swings when a port is built. Perf: about 4 to 6 draws, High only.
4. **Building rise and upgrade moment (S-M).** Now: storeys step up and reduced motion snaps them (not seen live, because no build decision was reached). Add storey scale-in with overshoot, a dust ring, coins flying from the payer's ledger row to the lot, a flag raise, and a crane drop for ports. Perf: 1 to 2 transient draws.
5. **Dice and the move (M).** Now: no dice at all, and the piece hops. Add two tumbling dice in the market square or a HUD pair with faces, a doubles highlight, a hop arc with squash on landing, a fading footprint trail, and rent coin carts visible at street zoom (`world/CoinCarts.tsx`). Perf: about 2 draws.
6. **Camera language (S).** Now: one follow camera plus a toggle. Add a dolly-in on a buy decision, a cut to the market square for auctions (DESIGN), an orbit to the Brig on jail, and a slow victory orbit at game over. Perf: free. Use cuts under reduced motion.
7. **District identity (M).** The silhouettes exist and read well. Add kelp drying racks, a reef sea wall, jade verdigris sheen, crown flag masts with vertex-shader flutter, and district-coloured ground patches on the sand ring. Perf: merge into the existing instanced meshes, so no new draws.
8. **Game-over celebration and sound (S-M).** Now: a beige wash plus a modal. Keep the world visible and orbit the winner, raise flags on every lot the winner owns, and add sailcloth pennants in seat colour (one per lot owned, so they carry meaning). Sound is optional, muted by default, with a toggle in Menu: dice clack, coin clink, gull ambience, harbour bell on purchase. Perf: about 1 draw.

## Keep during the rework

- The paper, brass and ink panel system with tabular figures and key hints.
- The ink-outlined low-poly district silhouettes in street view.
- Game-over win-rate copy tied to `results/`, with game count, player count, "the 40 bots" and the CI.
- Keyboard play: Esc skips tips and declines, Enter buys or bids, and the Tab order is sensible.
- Instancing, `autoUpdate=false` shadows refreshed on `boardVersion`, the DPR cap, and `frameloop` demand on Low.

## Open questions for the owner

- Should night follow rounds (all seats) or stay on turns? (F4)
- Should "replay" mean a new game with the same seed, or a recording viewer? (F14)
- Should "Scripted bot" expose all bot types? (F19)
