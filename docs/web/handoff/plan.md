# Handoff: plan

Branch: `plan` · Date: 2026-11-23 · Status: done

## What changed
- Added `docs/web/PLAN.md`: concept, what the engine already provides, runtime options with
  the recommendation and four spike criteria, the `GameSession` contract, tasks 1-8 with
  acceptance criteria, and the testing section.
- Added `docs/web/DESIGN.md`: HUD patterns per moment, colour and type tokens, spacing,
  radius and shadow rules, motion, z-layers, 3D art direction, and quality tiers.
- `docs/web/REFERENCES.md`: removed the Mobbin table and pointed to DESIGN.md.
- `prompts/04b-hud.md`: removed the two Mobbin instructions.

## Decisions made (and why)
- **Runtime A, Pyodide in a Web Worker.** It runs the exact engine and agents and hosts as
  static files. Fallbacks: Pyodide JSPI inside A, then option B (FastAPI) if spike
  criterion 1 or 2 fails twice. Option C (TypeScript port) is rejected.
- **No Mobbin** (owner decision, 2026-11-23). The Mobbin MCP was not connected anyway.
- **HumanSeat reuses `AgentStrategy`** (`src/saltmarket/rl/agent.py`) with a blocking
  `decide`, so the engine needs no hook.
- **PPO uses `two_player.npz` at 2-player tables and `main.npz` at 4-player tables.** DQN
  has only a 2-player model, so it is labelled as such at 4 players.
- **The critic is exported for both agents**, so lanterns can show true DQN Q-values and the
  replay can show a value river. Both are labelled "value estimate", because the values
  include reward shaping and are not win probabilities.
- Owner colours are close in brightness, so each seat also gets an emblem and an ink outline.
- The real repo is `DhemanthN/saltmarket_Monopoly_bot`. `prompts/06-deploy.md` and
  `prompts/DISPATCHER.md` still say `saltmarket_Monopoly_bot`; PLAN.md uses the real name.

## How to verify
- Commands: `git show --stat HEAD`, then read `docs/web/PLAN.md` and `docs/web/DESIGN.md`.
- What you should see: only files under `docs/web/` and `prompts/04b-hud.md` changed.
- Contrast numbers come from the WCAG 2.x formula. Model shapes came from loading
  `models/*.npz`.

## Tests
- Added: none (documentation only).
- Results: `ruff check .` passed. The change touches no Python, so `pytest -m smoke` was
  started but not waited on; it ran past the 2-minute tool limit on this machine.

## Left for later / known issues
- The wrong repo name in `prompts/06-deploy.md` and `prompts/DISPATCHER.md` is not fixed.
- Whether PPO and bot decisions match exactly under Pyodide (floating-point in
  `bots/forecast.py`, `rng.spawn` support) is untested until the spike.
- Font files are not yet downloaded. Task 3 adds them.

## What the next task needs to know
- Spike (task 1): criteria are in PLAN.md section 3. Fingerprint code is
  `src/saltmarket/sim/fingerprint.py`, goldens are `tests/data/golden_games.json`. Only
  numpy is needed for the engine and `NumpyPolicy`, and `data/board.json` and
  `data/cards.json` must ship with the package.
- Design system (task 3): tokens are in DESIGN.md, ready to copy into `tokens.css`.
