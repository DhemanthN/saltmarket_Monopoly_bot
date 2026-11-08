# Changelog

Notable changes to Saltmarket AI. Every number here comes from a file in `results/`.
Saltmarket is an original Monopoly-style game, so findings apply to Saltmarket only.

## [Unreleased]

Work in progress on separate branches. Results will be added here only after the runs
finish and their output is saved to `results/`.

### Planned

- **DQN agent** (`feat/dqn`): Double DQN with dueling heads, experience replay, and a
  target network, trained with the same opponents, curriculum, and 20M-decision budget
  as the 2-player PPO agent, then compared with significance tests.
- **Unseen opponents** (`feat/new-bots`): 14 new strategy bots kept out of training, used
  to measure how the PPO agent does against strategies it has never seen.
- **Performance** (`feat/perf`): profiling, engine speedups that keep results
  bit-identical for the same seeds, and a multi-core scaling benchmark.
- **Larger tournament**: after the branches merge, a rerun with all 40 bots targeting
  1,000,000+ games.

See [docs/ROADMAP.md](docs/ROADMAP.md) for goals and how each one will be measured.

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
