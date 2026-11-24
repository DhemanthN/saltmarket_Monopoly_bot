# Handoff: world (task 4a)

Branch: `world` · Date: 2026-11-23 · Status: done (design-critic SHIP at fc663dc, perf inside budget)

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
- The owner chose "keep fixing all 7 here" when the first design review returned NO-SHIP.
  Four review rounds followed, and the fourth returned SHIP.
- `piecePositions` moved to its own module so `Pieces.tsx` exports only components
  (React fast refresh rule).
- The perf probe turns off `gl.info.autoReset` and resets once per frame. The high-tier
  composer otherwise reset the counters on every pass.
- Outline hulls use polygon offset. This removed the z-fighting under the roofs.
- Night lifts each colour toward moonlight. Dark cells move up to 50% and light cells 15%, so
  basalt and cinder keep their shape. The night horizon haze is moonlit.
- Pieces, their outlines and blob shadows set `frustumCulled={false}`. Their instance
  matrices move every frame, so the bounding sphere from the first frame culled them.
- An empty storey slot is scaled to zero on every axis. Flattening only y left coloured
  plates behind.
- Mortgage shutters on stilt houses sit above the deck, as paper-deep slats on an ink frame.
- The camera follows the winner first, then a human who is still playing, then the first
  active seat. This lives in `follow.ts`, with tests. The street camera aims close and looks
  higher on portrait screens.
- `gl.shadowMap.enabled` is set in an effect, because the Canvas `shadows` prop is read
  only once and a runtime tier change would otherwise keep shadows on.
- `Sky.tsx` adds a dome running from horizon haze to the sky colour overhead, plus
  distant islets. The sea carries depth contours. The compass rose shows in chart view only.
- `Signboards.tsx` draws DOM signboards (drei `Html`) on brass leaders for the 3 spaces ahead
  of the followed piece, or 2 on portrait screens. Each shows the price, "<Seat> owns" or
  "<Seat> · mortgaged". A sign fades when its anchor leaves the central 80% of the frame.
  The Brig is always labelled.
- Harbours are drawn only for seats in play, in seat colours, because rent carts land there.
- The chart-view tilt-shift blur was cut from 0.18 to 0.07, so the board stays crisp.
- The light setup and the perf probe turn off `react-hooks/immutability` for their effects,
  because three.js renderer and scene objects are mutated by design.

## How to verify
- Commands: in `web/`, run `npm run typecheck`, `npm run lint`, `npm test` and
  `npm run preview:dev`, then open `/world`.
- What you should see: a fixture replaying on the atoll. Scrubbing to the end matches the
  engine's final state (tested).

## Tests
- Added:
  - `reduceEvents.test.ts`: every fixture reduces to the engine's `finalState`, the mid-turn
    cut is correct, the input is never mutated, and `boardVersion` changes only on board
    events.
  - `follow.test.ts`: reproduces the game-end camera bug on bots_3p, plus two cases for the
    human seat.
- Results: Vitest 54/54 pass. tsc and eslint are clean, and `npm run build:dev` passes. The
  Python engine was not changed.
- Reviews: design-critic SHIP at fc663dc, after rounds at 4b6c05f, 292da20, 128b3c1 and 8f23305.
  The perf-auditor passed every budget item at fc663dc; see
  `docs/web/perf/2026-11-23-world.md`.

## Left for later / known issues
- Signboards can still overlap when two lots far apart in depth line up on screen (seen at
  night on Ashfall Inlet and Emberstone). The fix is to project both and hide the farther one.
- On a 390 px wide screen, a long sign can touch the right edge. The fade tests the anchor
  point, not the sign's box.
- The mortgage shutter's new look has not been seen on screen yet, because no mortgaged lot
  was in frame during review.
- Auto tier may drop to low during cold-start jitter. This was not re-tested.
- Shadows can lag the sun direction by up to 5 turns between keyframes, which is within the
  budget.
- The production build warns that one chunk is over 500 kB.

## What the next task needs to know
- `WorldScene` takes `state` (from `reduceCount` or `reduceEvents`), `seatKinds` and an
  optional `tierOverride`.
- The HUD reads lantern positions from `anchors.ts`.
- `Signboard` (in `src/ui`) is reused in the world; keep its typography.
- `followSeatFor` in `follow.ts` decides which seat the street camera follows.
