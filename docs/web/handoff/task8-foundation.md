# Task 8 foundation handoff

## What changed
- **Fonts**: Cinzel (headings) and JetBrains Mono (numbers, HUD chrome) from `@fontsource`, latin subset, bundled by Vite (no CDN). Fraunces files and preload removed. IBM Plex Sans stays for body text. New tokens `--font-mono`, `--brass-lit` (#C9A24A, ornament only); `ornament` export and tests in `tokens.test.ts`.
- **HUD chrome** (`web/src/hud/Chrome.tsx`, `compass.ts`, `telemetry.ts`): corner brackets, vignette, compass bar from the real camera heading (north is world -Z), readout of turn, round (turn / seats), time of day and cash. Phones hide the brackets (the ledger strip owns the top edge) and the cash readout.
- **Loading chart** (`web/src/screens/LoadingChart.tsx`, `loadStages.ts`): SVG sea route, one stop per real load phase (runtime, Python, game code, models), ending on an X once the world has drawn two frames. Then it fades and releases the camera intro. Tall route on phones.
- **Camera** (`web/src/world/CameraRig.tsx`, `cameraBus.ts`, `cameraMotion.ts`): 2.5 s intro swoop (click or key skips), idle sway (only while the frame loop is continuous), mouse parallax (fine pointers, held still while a decision is open), `triggerCameraShake(intensity, duration)` with FOV punch, exported from `cameraBus.ts`.
- **Calm**: Menu checkbox (persisted in localStorage). `isCalm()` is true for the choice or `prefers-reduced-motion`; use it for trail and cannon effects.
- **Render pause**: rework A already paused on `visibilitychange`; now also while any `Dialog` is open (`modalOpened()` counter).

## Decisions
- Round = turn / seat count, since the engine turn counts each seat's turn.
- Brass `#C9A24A` measures 5.4:1 on night-panel and 2.0:1 on paper (not 3.6:1 as briefed); test asserts it is fine on dark chrome and too faint on paper.
- Loading chart replaces the 3D silhouette on the game screen, so Three.js is not needed to show it. `AtollSilhouette` remains for the error boundary.

## Left / unchecked
- Phone (390x844) live check not done; frame rate on a phone and `?perf=1` draw calls not measured.
- Bottom-right bracket sits near the existing Menu / Chart view buttons.
- Chrome and the HUD cards overlap at about 935 px width (ledger, coach).

## Verify
`npx tsc --noEmit`, `npx eslint .`, `npx vitest run` in `web/`; `npm run dev`, press Start, watch the route, then the swoop.
