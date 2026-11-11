# Roadmap

Version 2.0 is complete. Every workstream below is done, and its measured results are
in [CHANGELOG.md](../CHANGELOG.md) under [2.0.0] and in [RESULTS.md](../RESULTS.md).
This file keeps the plan as it was written, with each workstream's status, and the ideas
left for later.

No result appears here. Numbers go into `RESULTS.md` only after a script has run and
saved its output to `results/`.

## Goals

| Limitation in v1.0 | v2.0 workstream | Branch | Status |
| --- | --- | --- | --- |
| Opponents are not held out: the agent trained against the same 26 bots it was tested on | Unseen opponents | `feat/new-bots` | Done |
| Only one RL algorithm, so there is no baseline to compare PPO against | DQN comparison | `feat/dqn` | Done |
| Tournament size is limited by single-game speed | Performance | `feat/perf` | Done |
| 180,000 games across 26 bots | Larger tournament | after merge | Done |

## Workstreams

### Unseen opponents (done)

- **Goal:** measure how well the 2-player PPO agent plays against strategies it never
  trained against.
- **Approach:** add 14 new bots that differ from the existing 26, such as phase-adaptive,
  opponent-modeling, trade-heavy, and risk-aware strategies. Keep them in a separate
  held-out set that no training stage uses. Evaluate the existing agent without
  retraining it.
- **Measured by:** win rate with 95% Wilson intervals, overall and per opponent,
  compared with the 85.6% against the training bots. The best existing bot is the
  baseline.

### DQN comparison (done)

- **Goal:** find out whether PPO or DQN plays Saltmarket better.
- **Approach:** implement Double DQN with dueling heads, experience replay, a target
  network, and the same action masking. Check it on CartPole first. Train it with the
  same opponents, curriculum, and 20M-decision budget as the 2-player PPO run.
- **Measured by:** held-out win rates on the fresh seed set, a two-proportion test and
  bootstrap interval on the difference, wall-clock training time, and win rate against
  training steps.

### Performance (done)

- **Goal:** make large tournaments faster without changing any result.
- **Approach:** profile the engine, optimize the hot paths, and scale tournaments
  across CPU cores with deterministic per-game seeds.
- **Measured by:** games per second before and after, scaling across worker counts, and
  regression tests showing that seeded games produce identical outcomes and that worker
  count does not change results.

### Larger tournament (done)

- **Goal:** tighter estimates across a bigger bot pool.
- **Approach:** after the three branches merge, rerun the tournament with all 40 bots,
  targeting 1,000,000+ games, and rerun agent evaluation with more games per opponent.
- **Measured by:** updated win rates, intervals, and ratings, with every chart and table
  regenerated from the new results.

## Later

Ideas not scheduled yet:

- Count turn-cap wins as less than real wins in training, to address the 4-player
  stalled-game effect.
- Repeat training with several seeds and report the spread between runs.
- Search hyperparameters instead of using one fixed setting.
- Let the agent propose property swaps, not only cash offers.
- Make the close-variant held-out bots more distinct, or write a new unseen set.
- Fix the trade valuation that `mortgage_flipper` exploits (mortgaged spaces valued at
  list price), then rerun the tournament.
- Evaluate the DQN agent at 4 players on the v2 seeds.
