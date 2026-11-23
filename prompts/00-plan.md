Task 0: plan. Stay in plan mode for this whole task. Write no app code.

Read CLAUDE.md (including the "Web frontend" section), README.md, docs/rl.md,
docs/web/REFERENCES.md and docs/web/ANTI_SLOP.md. Use the `explorer` subagent to find
how strategies are called by the engine, how `NumpyPolicy` loads `.npz` weights, and
whether the PPO critic weights are exported.

Produce two files:

1. `docs/web/PLAN.md`
   - The concept: the 40-space loop as the ring road of an atoll; 8 groups as districts;
     street view and chart view; thought lanterns showing PPO top-3 action probabilities
     and DQN top Q-values; replay scrubber after the game.
   - Runtime options A (Pyodide in a Web Worker, blocking on a SharedArrayBuffer for
     human input), B (FastAPI server), C (TypeScript port), with your recommendation
     and the four spike pass criteria:
       1. seeded game in the browser runtime matches the desktop Python fingerprint
       2. a human seat pauses and resumes the engine
       3. PPO and DQN pick the same action as `NumpyPolicy.greedy` on 100 observations
       4. cold start under 8 s, cached under 2 s on the owner's laptop
   - The `GameSession` interface (methods, events, decision payloads) in TypeScript-ish
     pseudocode.
   - The task list 1-8 with acceptance criteria for each, matching prompts/.
   - The Testing section: what is tested and what deliberately is not.

2. `docs/web/DESIGN.md`
   - Use the Mobbin MCP to search each row of the Mobbin table in REFERENCES.md. Pick
     three examples per row and write one line on what to take from each.
   - Exact tokens: palette (base + 8 district accents + owner colours, all checked for
     contrast), two typefaces with fallbacks and why, type scale, 4 px spacing scale,
     radius and shadow rules, three motion durations with easing, z-layers.
   - Art direction for the 3D world: palette texture, outlines, fog, lighting by time of
     day, how each district's silhouette differs.
   - Quality tiers (high, medium, low-power) and what each turns off.

When both files are written, show me the plan summary in 15 lines and wait for my
approval. After approval: write `docs/web/handoff/plan.md`, commit, push.
