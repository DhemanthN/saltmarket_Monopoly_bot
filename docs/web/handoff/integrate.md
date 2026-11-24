# Handoff: integrate (task 5)

Branch: `integrate` · Date: 2026-11-23 · Status: done, waiting for the owner's playtest

## What changed
- `src/saltmarket/web/live.py`: `play_live`, the blocking game path the worker runs. It plays
  `ObservedGame` once. Before each human decision it flushes and sends the new events as JSON,
  then calls the JavaScript `ask`, which blocks in `Atomics.wait`. An `answers` prefix rebuilds a
  game in progress without asking. `scripts/record_fixtures.py` reuses its `final_state` and
  `result_view` helpers.
- Bundle helper tab: `scripts/build_web_runtime.py` (engine, `data/*.json`, the three model files
  under `models/`, so `paths.MODELS` resolves to `/app/models` unchanged),
  `web/scripts/fetch-pyodide.mjs` (Pyodide 314.0.8 core and the numpy wheel, sha256-checked, into
  `web/public/pyodide/v314.0.8/`), `web/vercel.json` (COOP/COEP, immutable caching), and their tests.
  Both outputs are gitignored. `npm run dev`, `npm run build` and `npm run build:dev` run
  `npm run runtime:assets` first.
- `web/src/runtime/`: `engineCore.ts` (boot and play, shared by the worker and the Node test),
  `engine.worker.ts`, `engineClient.ts` (one worker, its load progress and three shared
  `Int32Array` cells: answer flag, action, sticky abort), `workerSession.ts` (`WorkerSession`
  implements the `GameSession` contract, checks legality before waking the worker, and can
  `resume` on a fresh worker), `protocol.ts`.
- `web/src/store/`: one Zustand store (`gameStore.ts`). It owns the worker, keeps the event log,
  and releases events one at a time into the world reducer (`world/reduceEvents.applyEvent`) and
  the HUD reducer (`hud/state.applyEvent`). `pace.ts` decides which events wait one beat.
- Screens: `GameScreen.tsx` (world plus HUD, or the loading atoll), `RuntimeTrouble.tsx` (calm
  error panel with Retry and Back to the start), `loadCaption.ts`. `AtollSilhouette` takes
  `progress` and `caption`: lots rise in board order and the Home Quay signboard names the step
  ("Laying the reef 55%"). `SessionHud` was removed; the store replaces it. The start screen's
  table size is now a segmented control.

## Decisions made (and why)
- **Blocking path, not replay per submit**, as the contract handoff asked. A game runs once.
- **The engine starts loading on the start screen**, so it is usually ready by the time the
  person presses Start. Pressing Start earlier shows the same rising atoll until it is ready.
- **Caching:** the bundle (engine and weights) goes through Cache Storage, keyed by its content
  hash, and old bundles are deleted. Pyodide and numpy rely on the HTTP cache with immutable
  headers under a versioned path. Without Cache Storage (some private windows) it fetches.
- **Pacing:** the store waits `agentDelayMs` (700 ms from `startConfig.ts`) before each roll by a
  bot or agent seat and before each agent decision. The person's own events show at once, and a
  human decision appears only after every earlier event is on screen.
- **Retry** terminates the worker, loads a fresh one, and replays the person's answers. Events
  already shown are skipped by `seq`, so the game carries on where it stopped. Leaving mid-game
  sets the abort cell, so the same worker can start the next game.
- **Parity tolerance:** in `table_4p`, one explanation probability is 0.4972 in Pyodide and 0.4971
  on desktop (wasm against native float, in the 4th decimal). The parity test compares non-integer
  numbers within 5e-4. Fingerprints, final state, every integer and every string match exactly.
- The error panel makes the world and HUD behind it `inert`.

## How to verify
- Commands (PowerShell, venv active):
  - `ruff check .`, `pytest -q`, `pytest -m smoke`
  - `cd web; npm install; npx tsc --noEmit; npm run lint; npx vitest run; npm run build`
  - `npm run dev`, then open the printed URL.
- What you should see: the atoll's lots rise behind the start panel while the engine loads.
  Start plays a real game against the chosen opponents, with agent moves about 0.7 s apart.
  In a dev build, `window.__saltmarketRuntime.crash()` in the console shows the error panel,
  and Retry continues the same game.

## Tests
- Added: `tests/test_web_live.py` (every fixture through `play_live`, resume by prefix, illegal
  answer, no tqdm/multiprocessing/torch import), `tests/test_web_live_matrix.py` (helper: 2 and 4
  players against PPO, DQN and bots, DQN refused at 4), `web/src/runtime/parity.test.ts` (Node:
  Pyodide plus the built bundle, `vs_ppo_2p`, `vs_dqn_2p`, `table_4p`, about 7 s),
  `workerSession.test.ts`, `store/pace.test.ts`, `web/src/bundle/bundle.test.ts` (helper).
- Results: Vitest 113 passed in 14 files. `pytest -q` 510 passed. `pytest -m smoke` 426 passed in
  27.9 s (pre-task baseline 29.4 s on the same machine; runs vary by about 4 s with load).
  The matrix games and determinism checks were taken out of smoke (they run in the full suite);
  the DQN-refusal checks stay in smoke. No test was removed.
- Browser (Pane browser, dev server): full games finished at 2 players against PPO, DQN and the
  balanced bot, and at 4 players (you, PPO, balanced, expert). A crash mid-game followed by
  Retry finished the game with every `seq` in order.
- Reviews: perf-auditor passed every budget item (`docs/web/perf/2026-11-23-integrate.md`).
  design-critic returned NO-SHIP with 8 findings; the start, loading and error screen findings
  are fixed. The rest are listed below.

## Left for later / known issues
- design-critic findings not fixed here (they belong to world and HUD):
  - At 390x844 the decision sheet hides the player's piece. The camera should shift up by the
    sheet height (`world/CameraRig.tsx`, for example `camera.setViewOffset`).
  - Signboards can overlap (seen: Staghorn Key over Brain Coral Atoll). Known from task 4a.
  - Coach tip 1 covers the ledger row it describes. Anchor it below the rail.
  - Start screen at 390 px: small foggy atoll, panel touches the bottom edge.
- Switching from the loading atoll to the world remounts a canvas. The container now paints
  the sky colour, so the gap shows sky, not paper.
- Vercel builds need `python3` for `build_web_runtime.py` (task 6), or a committed bundle.
- The first switch to chart view stalled one frame for 5 s in headless Chrome (perf notes).
  Check it on real hardware.

## What the next task needs to know
- `useGameStore` is the only game state. The world reads `world` and the HUD reads `hud`; both are
  built by the existing reducers.
- `WorkerSession` implements `GameSession`. Add `result()` and `error()` reads there if the
  deploy or QA task needs them.
- Dev hooks: `window.__saltmarketRuntime.crash()` and `.store`.
