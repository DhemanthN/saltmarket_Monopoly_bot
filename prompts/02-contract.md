Task 2: contract. Read docs/web/handoff/spike-runtime.md and the GameSession section
of docs/web/PLAN.md. Start in plan mode.

Build the Python side and the shared contract, in the runtime the spike chose:

- `src/saltmarket/web/session.py`: `GameSession(seed, seats)` where seats are
  `human`, `ppo`, `dqn`, or a bot name. Methods: start, current decision (kind, legal
  actions, amounts), submit(action), and an event log.
- `HumanSeat`: a Strategy whose decisions come from `submit`. It only ever offers legal
  actions (reuse the masks from `rl/encoding.py`) and rejects illegal ones.
- `AgentSeat`: wraps `NumpyPolicy` for PPO and DQN and records an explanation with
  every move: top 3 legal actions with probabilities (PPO) or Q-values (DQN), plus the
  critic's value if those weights exist.
- Events as plain JSON: roll, move (with every space passed), buy, auction start/bid/
  win, rent paid, build, sell, mortgage, unmortgage, trade offer/result, brig in/out,
  bankrupt, game over. Each event carries the turn number.
- `scripts/export_contract.py`: writes `web/src/contract/types.ts` from the Python
  dataclasses so the two sides cannot drift.
- `scripts/record_fixtures.py`: records 5 full games as JSON to `web/fixtures/`
  (seeds fixed; at least one vs PPO and one vs DQN; one with an auction, a trade, and a
  bankruptcy).

Tests (use `test-writer`): human-seat legality, GameSession round trip vs engine run
directly, agent explanation present on every agent move, fixture files load.

Handoff, commit, push.
