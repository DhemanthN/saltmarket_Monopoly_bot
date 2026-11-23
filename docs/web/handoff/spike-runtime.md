# Handoff: spike-runtime

Branch: `spike-runtime` · Date: 2026-11-23 · Status: done, waiting for the owner's gate review

## Decision
**Runtime A (Pyodide in a Web Worker) is chosen.** Criteria 1, 2 and 3 pass on the first attempt.
Criterion 4 passes cold (5.2 s against 8 s) and **fails cached (4.7 s against 2 s)** after two
attempts. Because only criterion 4 failed, option B was not built. The owner should decide
whether the 2 s cached target stands (see "Criterion 4" below).

## Results

| # | Criterion | Result | Evidence |
| --- | --- | --- | --- |
| 1 | Same fingerprints as desktop for 10 seeds | **Pass** | `node node_check.mjs` (in `spikes/runtime/`): 2 players 10/10 identical, 4 players 10/10 identical, compared field by field (winner, turns, net worths, sha256) with `tests/data/golden_games.json`. Pyodide numpy 2.4.6, desktop numpy 2.5.4. 0.4 s and 0.8 s for the 20 games. |
| 2 | Human seat pauses the engine and resumes from a page choice | **Pass** | Node: `node node_human.mjs`: 423 decisions each blocked in `Atomics.wait` and resumed, result `{"winner": 1, "turns": 209, "events": 497}`, identical to desktop `python desktop_human.py` (same scripted choices). Browser: `node serve.mjs`, Pane browser at `http://localhost:5199/`, `crossOriginIsolated=true`, `SharedArrayBuffer` available in the worker. Two real mouse clicks each resumed the engine and showed the next decision. With `?auto=1` the full game finished in the browser with the same result as desktop. JSPI fallback not needed. |
| 3 | PPO and DQN pick the same action as `NumpyPolicy.greedy` | **Pass** | `node node_check.mjs`: PPO (`two_player.npz`) 100/100 identical, max logit difference 2.1e-6. DQN (`dqn_two_player.npz`) 100/100 identical, max logit difference 6.8e-8. The 100 observations and masks come from `record_observations.py` (every 7th decision of seeded 2-player games with random legal play), saved in `fixtures/observations.npz`. |
| 4 | Ready in under 8 s cold and under 2 s cached | **Cold pass, cached fail** | Browser, this laptop, worker created to engine ready (Pyodide, numpy, tqdm, package, three npz files). Cold (`no-store`): 5.78, 5.23, 5.07 s, median **5.23 s**, 10.8 MB transferred (brotli). Cached (immutable): 4.90, 4.64, 4.65 s, median **4.65 s**, 0 bytes transferred. |

### Criterion 4 detail
- Cached phase split (one run): `loadPyodide` 2.68 s, numpy + tqdm 0.52 s, unpack and models
  0.04 s, `import saltmarket` 1.49 s. Time is compute, not network, so cached is barely
  faster than cold on localhost.
- Cold on localhost hides real network time. At 10.8 MB, add roughly 1.7 s on a 50 Mbit/s line.
- Attempt 1: baseline above. Attempt 2: shipped precompiled unchecked-hash `.pyc` files
  (`build_bundle.py --pyc`). No gain (1.60 s for the import, 5.17 s total), so the import cost
  is numpy initialisation and module execution, not compiling.
- Untested ideas, not tried because the two attempts are used: Pyodide memory snapshots
  (`makeSnapshot`), dropping `tqdm` (only imported because `sim/fingerprint.py` imports
  `sim/tournament.py`), and relying on the browser's wasm code cache with a real Vercel
  deployment. Cache Storage was not implemented in the spike; the HTTP cache was used.
- Practical view: a 4-5 s load behind the "atoll being built" progress screen (task 5) is
  acceptable, and it happens once per page load. Owner to confirm or relax the 2 s target.

## What changed
- New `spikes/runtime/` (throwaway, not in `web/`): `build_bundle.py`, `record_observations.py`,
  `desktop_human.py`, `spike_py/loader.py`, `common.mjs`, `node_check.mjs`, `node_human.mjs`,
  `serve.mjs`, `index.html`, `worker.js`, `fixtures/observations.npz`, `package.json` (pyodide
  `314.0.8`, Python 3.14.2) and its lockfile.
- No change under `src/` or `tests/`. `git diff main --stat -- src tests` is empty, so every
  existing test and fingerprint is untouched. No engine hook was needed: the human seat is an
  `AgentStrategy` whose `decide` blocks.

## How to verify
```powershell
cd spikes/runtime
$env:PYTHONPATH = "<worktree>\src"      # see note below
..\..\..\..\.venv\Scripts\python.exe record_observations.py
..\..\..\..\.venv\Scripts\python.exe build_bundle.py
npm install
node node_check.mjs      # criteria 1 and 3
node node_human.mjs      # criterion 2 in Node
..\..\..\..\.venv\Scripts\python.exe desktop_human.py   # desktop result to compare
node serve.mjs           # browser: http://localhost:5199/ (add ?auto=1 to play unattended)
```
`curl http://localhost:5199/mode?cold=1` makes the server send `no-store` (cold runs);
`?cold=0` restores immutable caching. Ready time is `window.spike.readyMs`.
Checks: `ruff check .` clean, `pytest -m smoke` 401 passed in 27.8 s.

## Decisions made (and why)
- Wheels (numpy, tqdm) are self-hosted from `vendor/` (fetched once by the `pyodide` npm package),
  Pyodide core from `node_modules/pyodide/`, so nothing loads from a CDN under COEP.
- Server compresses with brotli to mimic Vercel transfer sizes.
- Spike has its own torch-free `load_weights` because `rl/train.py` imports torch.

## Left for later / known issues
- Task 5 should move `load_policy` out of `rl/train.py` into a torch-free module (with tests),
  and avoid the `tqdm` and `multiprocessing` imports that come with `sim/tournament.py`.
- The editable install of `saltmarket` in `.venv` points at the main checkout, not this worktree.
  Set `PYTHONPATH` to the worktree `src` when running Python here.
- Only 2-player models and PPO/DQN parity at 2 players were tested. `main.npz` (4 players) and
  `bots/forecast.py` parity are covered by criterion 1 (all bots across 20 games) but not by a
  separate agent check.
- Not tested: Safari/Firefox, mobile, memory use, long games blocking while the tab is hidden.

## What the next task needs to know
- Bundle layout that worked: unpack a zip with `src/saltmarket/**` and `data/*.json` to `/app`,
  add `/app/src` to `sys.path`. `engine/board.py` finds `data/` as `parents[3]`, so no code change.
- Page needs `Cross-Origin-Opener-Policy: same-origin` and
  `Cross-Origin-Embedder-Policy: require-corp` (see `serve.mjs`); add them in `web/vercel.json`
  and the Vite dev server.
- Blocking pattern: worker passes a JS function into Python as `decide`, which posts the legal
  actions to the page and calls `Atomics.wait` on an `Int32Array` over a `SharedArrayBuffer`.
  Page writes the action to cell 1, sets cell 0 to 1 and calls `Atomics.notify`.
