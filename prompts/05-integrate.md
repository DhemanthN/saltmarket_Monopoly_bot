Task 5: integrate. Read the handoffs for contract, world and hud. Start in plan mode.

Wire it together:
- `web/src/runtime/`: the Web Worker running the chosen runtime, exposing the
  GameSession contract to the page. Show load progress as the atoll being built, not a
  spinner. Cache the runtime and model weights after first load.
- One store (Zustand or similar) holding the event log; world and HUD both read from
  `reduceEvents`.
- Human decisions from the HUD go to `submit`; agent moves play with a short readable
  delay so a person can follow them (configurable, default about 700 ms).
- Full games against PPO, DQN and bots, at 2 and 4 players.
- Errors in the worker surface as a calm in-world message with a retry, never a blank
  screen.

Tests: an engine-parity test that runs 3 seeded games through the worker path in Node
and matches desktop fingerprints (`test-writer`). Run the whole Python suite and
Vitest.

Then ask me to playtest locally: print the exact commands (`cd web`, `npm install`,
`npm run dev`) and what to try. Fix what I report. Handoff, commit, push.
