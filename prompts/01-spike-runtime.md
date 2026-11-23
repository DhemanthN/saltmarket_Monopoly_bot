Task 1: spike-runtime. Read docs/web/handoff/plan.md and the runtime section of
docs/web/PLAN.md. Start in plan mode.

Goal: decide, with evidence, how the engine runs for the website. Build the smallest
throwaway proof in `spikes/runtime/` (not in `web/`).

Test option A (Pyodide in a Web Worker) against the four criteria:
1. A seeded game in Pyodide (run it in Node with the `pyodide` npm package for the
   automated check) gives the same event fingerprint as desktop Python for 10 seeds.
   Reuse the fingerprint code from tests/test_performance.py.
2. A human seat pauses the engine and resumes with a choice sent from the page. In the
   browser, the worker blocks on a SharedArrayBuffer with Atomics.wait; this needs the
   headers `Cross-Origin-Opener-Policy: same-origin` and
   `Cross-Origin-Embedder-Policy: require-corp` on the dev server.
3. PPO (`models/` two_player run) and DQN (`models/dqn_two_player.npz`) pick the same
   action in Pyodide as `NumpyPolicy.greedy` on 100 recorded observations.
4. Time cold start and cached start to a ready engine on this laptop.

Rules:
- Two genuine attempts per criterion, then stop and record what failed.
- If 1 or 2 fails, sketch option B (FastAPI + thread per game) and prove criteria 1-3
  for it instead.
- Do not change engine behaviour. If the engine needs a hook for a human seat, add it
  with a test and keep every existing test and fingerprint identical.

Finish with a table in `docs/web/handoff/spike-runtime.md`: criterion, result
(pass/fail), evidence (command + numbers), and the chosen runtime. Commit, push, and
stop. The owner reviews this gate before anything else starts.
