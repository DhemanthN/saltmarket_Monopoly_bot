Task 4a: world. Read docs/web/handoff/contract.md and design-system.md, then
DESIGN.md (art direction and quality tiers). Start in plan mode. Runs at the same
time as task 4b; do not touch `web/src/hud/`.

Build `web/src/world/`, driven only by replaying `web/fixtures/*.json`:
- The atoll: a ring road with 40 spaces, a lagoon in the middle with the market square
  and the Brig rock, 8 districts each with its own silhouette and accent.
- One palette texture for all colours; ink outlines; fog.
- Buildings instanced per type; levels grow storey by storey on build events and
  shrink on sells; owner colour on sails and awnings; mortgaged lots close shutters.
- Pieces hop space by space along the road on move events; rent sends a coin cart to
  the owner's harbour; the sun arc follows the turn number.
- Cameras: street view (third person behind the human's piece, smooth follow) and
  chart view (tilt-shift god view); toggle with one key and one button.
- Thought lantern anchor above each agent piece (the HUD task fills its content).
- A pure `reduceEvents(events, turn)` -> world state function; the scene renders state,
  never events directly. Test it with Vitest on the fixtures (`test-writer`).
- Quality tiers with drei PerformanceMonitor; low-power mode; DPR capped at 2; shadow
  map refreshed only when the board changes; expose `window.__saltmarketPerf` in dev.
- A replay debug control (play, pause, scrub) for development.

Run `perf-auditor` and `design-critic` before calling it done. Handoff, commit, push.
