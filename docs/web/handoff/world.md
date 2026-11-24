# Handoff: world (task 4a)

Branch: `world` · Date: 2026-11-23 · Status: blocked (design-critic NO-SHIP, fixes in progress)

## What changed
- `web/src/world/`: the 3D atoll scene. It has 8 district silhouettes, one palette texture,
  ink outlines, fog, instanced buildings and storeys, hopping pieces with owner pennants, coin
  carts, a sun arc over a 24-turn day, street and chart cameras, thought-lantern screen
  anchors (`anchors.ts`) and quality tiers (`quality.ts`).
- `reduceEvents.ts`: a pure reducer from contract events to the world state.
- `dev/ReplayPage.tsx`: dev-only `/world` page. It replays any fixture with play, pause,
  speed (1x, 4x, 16x), an event scrubber and a quality-tier override.
- `window.__saltmarketPerf` (dev builds): tier, DPR, fps, draw calls, triangles and shadow
  map refreshes.
- Perf numbers: `docs/web/perf/2026-11-23-world.md`.

## Decisions made (and why)
- `piecePositions` moved to its own module so `Pieces.tsx` exports only components
  (React fast refresh rule).
- The perf probe turns off `gl.info.autoReset` and resets once per frame. The high-tier
  composer otherwise reset the counters each pass and reported 1 draw call.
- The outline hulls use polygon offset. This removed the black and green z-fighting under
  the roofs.
- The night palette now mixes 20% toward the night background, down from 45%, and the
  night lights are brighter. At 45% the district colours were lost.
- Owner flags are small pole pennants that turn only around the vertical axis. They are no
  longer large squares turned to face the camera.
- Light setup turns off `react-hooks/immutability` for one block, because three.js renderer
  and scene objects are mutated by design.

## How to verify
- Commands: in `web/`, run `npm run typecheck`, `npm run lint`, `npm test` and
  `npm run preview:dev`, then open `/world`.
- What you should see: a fixture replaying on the atoll. Scrubbing to the end matches the
  engine's final state (tested).

## Tests
- Added: `reduceEvents.test.ts`. It checks that every fixture reduces to the engine's
  `finalState`, that the mid-turn cut is correct, that the input is never mutated, and that
  `boardVersion` changes only on board events.
- Results: Vitest 51/51 pass. tsc and eslint are clean. The Python engine was not changed.

## Left for later / known issues
Design-critic NO-SHIP items still open:
1. Night lighting: the second attempt (commit 3301727) has not been re-reviewed yet.
2. At night one pennant was seen with no piece body under it. The cause is not found yet.
3. A dark box remains under one stilt house, and green planes hang under the stilt-house
   roofs.
4. Street camera framing leaves half the frame empty, and no piece is visible at game end.
5. The sky is a flat band with a hard seam into the sea. The chart sea has no treatment.
6. Signboards are blank. DESIGN.md asks for prices on signboards.
7. The lagoon rock and hexagon pads in chart view carry no game state (ANTI_SLOP item 8).

Perf (all within budget) has these known issues:
- A first-switch stall into high-tier chart view.
- Auto tier can drop to low during cold-start jitter.
- Shadows can lag the sun direction by up to 5 turns.

## What the next task needs to know
- `WorldScene` takes `state` (from `reduceCount` or `reduceEvents`), `seatKinds` and an
  optional `tierOverride`.
- The HUD reads lantern positions from `anchors.ts`.
