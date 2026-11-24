# Rework A, world slice (helper tab "world")

Commits: `f470032` (world, App, vite) and `eef7e0d` (runtime split). Not pushed.

## Fixed
- F1: `world/chartFit.ts` finds the camera distance that fits the ring in the open frame (width and height above `bottomInset`). Tested at 390x844. Chart view centres the ring in the open area.
- F4: sky, haze and lights ease day to night through dusk and back through dawn, still counted in turns (24 per day). Night palette swaps at half dark. `WorldScene` sets `document.documentElement.dataset.mood`, so the HUD night panel applies with no screen change. Windows and lamps glow at night through a second emissive palette texture (`LitMaterial`, `palette.emissiveTexture`). New palette cell `world.glow`. Game now starts in daylight.
- F5: replaced the drei `PerformanceMonitor` (it counted sparse demand-mode frames as a slow machine) with `TierGovernor` (1 s windows: 3 slow windows down, 5 healthy windows up, no retry of a failed tier for 60 s). Auto Low runs a 7 s continuous probe every 20 s so it can climb back. Desktop starts on High, phones on Medium. Reduced motion no longer forces Low.
- F6, F7: signboards hide when they would overlap a nearer one, stay clear of the ledger rail (356 px, mirrors `LedgerRail.module.css`) and use ledger names ("Yours", "Wave owns"). Non-property markers get a pennant colour by kind and a lamp.
- F21: `beforeunload` warning while a game is in progress (App.tsx). Quality choice persists via `useQualityChoice()` in `world/quality.ts` (see Main agent wiring).
- F23: `toNonIndexed` warnings gone (`nonIndexed()` helper), shadows use `"percentage"`. The `THREE.Clock` warning comes from @react-three/fiber 9.8; `world/quietUpstream.ts` drops that one message.
- F24: sun emblem has an open centre; each seat has its own piece silhouette (pawn, tower, gem, anchor post). Not the task 8 piece set.
- F26: `GameScreen` is lazy; Three.js and R3F are one `three` chunk. Main chunk 34 kB (was 1.23 MB). `three` chunk 1.15 MB (314 kB gzip) loads at Start. ChartTiltShift/postprocessing stay in their own lazy chunk (104 kB).
- F27: `?perf=1` enables `window.__saltmarketPerf` in any build, now with `textures` and `geometries`.
- F28: weights ship as `model.<name>.<hash>.npz` beside a 111 kB code zip. The worker fetches only the models the seats need (`modelsFor`). A PPO 2p game downloads about 1.2 MB of runtime instead of 3.4 MB. Weights are float and do not compress, so splitting was the lever.
- F29: not reproduced as a bug in code. The drei monitor was the only per-frame consumer in demand mode and is gone. Needs the perf-auditor on Low to confirm.
- F30: Brig spot no longer allocates per frame; chart pose no longer clones vectors; geometries disposed on unmount (`useDispose`). Pixel ratio capped at 1.5 on touch devices. Rendering stops when the tab is hidden.

## Main agent wiring (screens are not mine)
- `GameScreen`: `const [quality, setQuality] = useQualityChoice();` (import from `../world/quality`) to keep the quality setting across reloads.
- `GameScreen`: pass `paused` to `WorldScene` while a full-screen modal is open.
- Dev console showed once a React `removeChild` NotFoundError around "Skip tips" (HUD side, not reproduced on toggling camera).

## Verify
`npx tsc --noEmit`, `npx eslint .`, `npx vitest run` (140 pass), `pytest -m smoke` (426 pass). Live: desktop 1645x860 and a 603x831 portrait viewport against `vite --port 5190`. The 390x844 resize was refused by the browser tool; phone fit is covered by `chartFit.test.ts`.

## Skipped
Stars, moon disc and bloom (task 8). Night stays turn-based by owner answer.
