# Changelog

Notable changes to Saltmarket AI. Every number here comes from a file in `results/`.
Saltmarket is an original Monopoly-style game, so findings apply to Saltmarket only.

## [Unreleased]

Nothing yet. Ideas for later are in [docs/ROADMAP.md](docs/ROADMAP.md).

## [2.0.0] - 2026-11-11

Unseen opponents, a second learning algorithm, a faster engine, and a tournament eleven
times larger. See [RESULTS.md](RESULTS.md) for the full findings and
[docs/ROADMAP.md](docs/ROADMAP.md) for the plan.

### Added

- **14 held-out bots** in `src/saltmarket/bots/heldout/`, kept out of every training
  stage, for 40 bots in all. Each survived 1,000 fuzzed games with invariants checked
  (`bot_fuzz_heldout.csv`). `scripts/heldout_overlap.py` measures how often each one
  plays exactly like a training bot (`heldout_overlap.csv`).
- **40-bot tournament**: 2,060,000 games and 861,572,594 player turns. That is 1,560,000
  2-player games (2,000 per pair) and 500,000 4-player games (125,000 tables in all four
  rotations). 95% Wilson intervals are no wider than ±0.35 points at 2 players and ±0.44
  at 4 (`tournament_summary.json`).
- **Double DQN agent** with dueling heads, n-step replay, and a target network, written
  from scratch and checked on CartPole. It trained under the same conditions as the PPO
  specialist (`models/dqn_two_player.npz`, `training_log_dqn_two_player.csv`).
- **v2 evaluation**: a new seed set and 1,000 games against each of the 40 bots per agent.
  Per-game outcomes are saved, so agents on the same schedule are compared with McNemar's
  paired test.
- **Results**, all at 2 players:

  | Agent | 26 training bots | 14 unseen bots |
  | --- | --- | --- |
  | PPO specialist | 85.6% (CI 85.1–86.0) | 75.4% (CI 74.7–76.1) |
  | DQN | 81.4% (CI 81.0–81.9) | 72.5% (CI 71.8–73.3) |

  - PPO won 82.0% overall (CI 81.6–82.4), 1st of 41 entrants, and beat every bot
    head-to-head. Sources: `rl_eval_summary_two_player_v2_all.json`,
    `rl_eval_summary_dqn_two_player_v2_all.json`.
  - PPO beats DQN by 3.7 points (bootstrap CI 3.2–4.2, McNemar p = 2.4 × 10⁻⁵¹), and
    by 2.9 points against the unseen bots alone (`ppo_vs_dqn.json`).
  - The best training bot, `auction_sniper`, drops 13.2 points against the unseen bots,
    more than PPO's 10.1 (`pool_win_rates.csv`).
- **Benchmark** (`scripts/benchmark.py`, `benchmark.json`, measured with the 26 training
  bots):
  - single-process speedups of 1.93x at 2 players, 2.71x at 4 players, and 2.24x on the
    tournament mix
  - 560 games per second at 16 workers, 25x the old engine on one core
- **Golden fingerprints** of 100 seeded games, recorded before the speed work, prove the
  engine still plays every game bit for bit the same (`tests/test_performance.py`).
- `scripts/project_stats.py` totals games, turns, lines of code, and tests
  (`project_stats.json`). The project has now simulated 2,478,889 games across the
  tournament, evaluations, fuzz tests, and training. It has 9,773 non-blank lines of
  Python and 461 tests, up from 333.

### Changed

- The engine caches ownership views and draws dice in batches, and bots search only
  where an action is possible. Results are unchanged for every seed.
- One-worker tournaments run in-process. Results are identical for any worker count or
  chunk size, which tests check.
- Every chart and table was regenerated from the 40-bot tournament and the v2
  evaluations. Charts mark held-out bots in their own color.
- New strongest bot: the held-out `mortgage_flipper` leads clearly at 4 players (49.6%)
  and is tied for first at 2 (78.5%, against 78.4% for `auction_sniper`). `auction_sniper` fell from 17th of 26
  to 33rd of 40 at 4 players (v1 figure from `four_player_win_rates.csv` in the `v1.0.0`
  tag).
- `evaluate.py` takes `--seed-set` and `--pool`, replacing `--fresh-seeds`.
- `docs/RESUME_UPDATE.md` is no longer tracked, at the owner's request.

### Fixed

- Review before merging removed doc claims that no saved file backed:
  - a 5,000-game byte comparison
  - the cause of the 24-worker slowdown
  - several DQN diagnostic figures
  - the DQN first run's stopping point (4.88M decisions, not 4.1M)
- The PPO vs. DQN comparison now uses a paired test. Both agents play the same seeds, so
  the earlier unpaired test was conservative.

## [1.0.0] - 2026-11-06

First complete version: rules engine, bots, tournaments, PPO agent, analysis, and docs.

### Added

- **Rules engine** for Saltmarket: an original 40-space board and 32 cards
  (`data/board.json`, `data/cards.json`), rent schedules, auctions, trading, mortgages,
  building shortages, the Brig, and bankruptcy.
- **26 strategy bots**, described in [docs/strategies.md](docs/strategies.md).
- **Monte Carlo tournaments**: 130,000 two-player games (400 per pair, seats alternated)
  and 50,000 four-player games (12,500 tables in all four rotations), with 95% Wilson
  intervals no wider than ±1.1 points and Bradley-Terry ratings on an Elo scale.
- **PPO agent** written from scratch in PyTorch: a 266-feature observation, 108 actions
  with masking, a four-stage curriculum ending in self-play, and two training runs of
  20 million decisions each. See [docs/rl.md](docs/rl.md).
- **Results**: the 2-player specialist won 85.6% of 10,400 fresh-seed games (95% CI
  84.9–86.2) against the 26 bots and beat every bot head-to-head. The mixed agent won
  40.7% of 10,000 four-player games. Details and limitations are in
  [RESULTS.md](RESULTS.md).
- **Validation**: 333 tests, 10,000 fuzzed random-bot games with zero invariant
  violations, and an exact Markov chain check over 1,863,535 rolls (0.16% total
  variation distance).
- **Analysis**: 11 charts in `results/figures/`, built with pandas and matplotlib.
- **CI**: GitHub Actions runs ruff and all non-slow tests on every push.
- **Reproducibility**: `scripts/reproduce_all.py` rebuilds every result, and `--quick`
  checks the whole pipeline in about 3 minutes.

### Fixed

- Group-value statistics counted groups a winner received from a bankrupt player, which
  made nearly every group look decisive. Groups now count only when earned by purchase,
  auction, or trade. A full rerun produced identical win-rate tables, showing only the
  measurement changed.
