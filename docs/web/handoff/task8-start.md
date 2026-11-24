# Task 8, start slice (helper "start")

## Done
- Start screen option A: procedural pirate ship (about 2.1k triangles, three merged meshes, no download) in `web/src/screens/ship/`. Lazy chunk, own Canvas box beside the panel (desktop: left of a 400 px panel; under 900 px wide: top 40%, panel is a bottom sheet). Still frame under reduced motion or Calm.
- Mode picker (Quick match, vs PPO, vs DQN, Table of 4, Watch bots) in `startConfig.ts` (`Mode`, `buildModeConfig`, `modeAllowed`, `modeSize`) with tests. DQN is disabled with a note at 3 or 4 players. Old `buildConfig` and the seat table, seed and named bot set are unchanged.
- Carved and brass pieces: `web/src/world/pieceModels.ts` (body mesh in wood/brass/iron cells, cloth mesh in owner colour), used by `Pieces.tsx`. The flag with the emblem is kept on each piece.
- Spyglass cursor + lot label (`SpyglassCursor.tsx`, `hoverStore.ts`, `hoverPick.ts`) and ember trail (`CursorFx.tsx`, `emberPool.ts`, max 30 points, 0.6 s). Hover uses a throttled ground-plane test (no mesh raycast), label is lot name plus district. Touch tap shows the label for 2.5 s. Mouse-only, off under reduced motion or Calm.
- Mounted in `WorldScene.tsx`: `<CursorFx />` in the Canvas, `<SpyglassCursor />` beside the corner controls.

## For other agents
- Calm: I read `document.documentElement.dataset.calm === "on"` (`world/motionPref.ts`). The foundation Calm toggle must set that attribute, or change `calmOn()`.
- `pieceGeometry` in `world/geometry.ts` is now unused; the world agent can delete it.
- `StartScreen` no longer draws `AtollSilhouette`; it shows load progress as a status line. The foundation loading screen should take over after Start.
- Cursor label has no key hint ("Enter"): nothing in the world is activatable by key yet.

## Verify
`npm run dev`, open `/`. vitest 181 pass, eslint and tsc clean at my last run.

## Not verified
- Phone layout and Watch bots mode (all-bot game through GameScreen) not run live. Session supports no-human tables, GameScreen not tested with one.
- Draw calls (`?perf=1`) and phone fps not measured. Ship is 3 draw calls, pieces up to 4 per seat, trail 1.
