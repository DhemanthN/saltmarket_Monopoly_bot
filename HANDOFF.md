# Handoff

Living progress file. A fresh session should read `CLAUDE.md`, then this file.

## Status

| Milestone | Description | Status |
| --- | --- | --- |
| M1 | Project scaffold | Done |
| M2 | Rules engine | Done |
| M3 | Strategy bots (20+) | Done |
| M4 | Monte Carlo tournament | Done |
| M5 | RL agent (PPO) | Done |
| M6 | Data analysis and charts | Done |
| M7 | Documentation and polish | Done |
| Final | `docs/RESUME_UPDATE.md` | Done |

## Done so far

- `data/board.json`, `data/cards.json`: the original 40-space board and 32 cards.
- `src/saltmarket/engine/`:
  - `config.py`: `GameConfig` with every tunable rule.
  - `board.py`, `cards.py`, `dice.py`: data loading, decks, injectable dice.
  - `state.py`: `GameState`, `PlayerState`, `IllegalMoveError`.
  - `rules.py`: read-only queries (rent, `can_build`, net worth, and so on).
  - `bank.py`: every cash and building change, each checked for legality.
  - `trade.py`: `TradeOffer`, `is_valid_trade`, `execute_trade`.
  - `actions.py`: `BrigChoice`, `Liquidation`.
  - `game.py`: `Game` loop, cards, debts, auctions, bankruptcy.
  - `invariants.py`: `check_invariants`, run every turn when `debug=True`.
  - `markov.py`: exact landing probabilities, independent of `game.py`.
- `src/saltmarket/bots/`: `base.py` (`Strategy`, passive by default), `random_bot.py`,
  `heuristic.py` (`HeuristicBot`, configurable base), `values.py` (board evaluation),
  `catalog.py` (26 named bots, `BOTS`, `make_bot`).
- `docs/strategies.md`: one paragraph per bot, enforced by a test.
- `src/saltmarket/sim/`: `fuzz.py`, `landing.py`, and `tournament.py` (schedules, parallel
  play, resumable chunks in `results/raw/`), all using spawn.
- `src/saltmarket/analysis/`: `style.py` (chart style), `tournament_stats.py` (Wilson
  intervals, win rates, head-to-head, Bradley-Terry ratings, group value).
- `scripts/fuzz.py`, `scripts/fuzz_bots.py`, `scripts/landing_frequency.py`,
  `scripts/simulate.py`: write to `results/`. `simulate.py` runs 130,000 two-player and
  50,000 four-player games in about 6 minutes.
- Tests: see the latest review gate in the log below.
- See `git log` for the latest commit.

## Paused (2026-11-08, branch `feat/dqn`, DQN comparison task)

Paused at the owner's request. Nothing is running.

**Done and committed:** Double DQN with dueling heads, replay, a target network,
epsilon-greedy, and n-step returns (`rl/dqn.py`). Also NumPy-only collection
(`rl/dqn_workers.py`), resumable training (`rl/dqn_train.py`, `scripts/train_dqn.py`),
comparison stats (`analysis/compare.py`), the chart function (`plots.agent_comparison`),
`scripts/compare_agents.py`, `evaluate.py --label`, `tests/test_dqn.py` (27 tests,
including the slow CartPole and resume tests, all passing), `tests/test_compare.py`
(7 passing), and the DQN section of `docs/rl.md`.

**Training reached:** 10,240,000 of 20,000,000 decisions (round 1000, 79,600 gradient
steps, 1,166 s of training time). Last checkpoint: `checkpoints/dqn_two_player/latest.pt`
plus `checkpoints/dqn_two_player/replay.npz` (1.2 GB, full buffer). The log
`results/training_log_dqn_two_player.csv` ends at the same round, 1000, and is left
uncommitted until the run finishes. Attempt 1 (stalled, see `docs/rl.md`) is kept in
`checkpoints/dqn_two_player_attempt1/` and `results/training_log_dqn_two_player_attempt1.csv`.

**Resume training** (same run name, same total; it continues from round 1000):

```powershell
.\.venv\Scripts\Activate.ps1
python scripts/train_dqn.py --steps 20000000 --run dqn_two_player
```

Notes for the resume. The saved seconds count only training time, so total wall-clock
time stays comparable. Worker seeds are derived from the round number, so a resumed run is
reproducible but not bit-identical to an uninterrupted run. Other sessions were using the
CPU during training, which slows game collection, so the wall-clock comparison with PPO
(1,206 s, measured without that load) needs that caveat.

**Left from the task list:**
1. Finish training (resume command above). It writes `models/dqn_two_player.npz`.
2. `python scripts/evaluate.py --run dqn_two_player --fresh-seeds --label dqn`, which
   writes the new `results/rl_eval_*_dqn_two_player_fresh.*` files.
3. `python scripts/compare_agents.py`, which writes `results/ppo_vs_dqn*.{json,csv}` and
   `results/figures/ppo_vs_dqn.png`. Look at the chart.
4. Add "PPO vs. DQN" to `RESULTS.md` and a results paragraph to the DQN section of
   `docs/rl.md`. Caveat: training-curve win rates compare near-greedy DQN (epsilon 0.02)
   with sampled PPO, so only the fresh-seed evaluation is a fair skill comparison.
   Partial curves, which are not final: from about 2M decisions, DQN's pooled training
   win rate was 72-79% against PPO's 41-64%.
5. Run `ruff check .`, the full `pytest`, and `pytest --cov`, update the test count in
   the README, commit the results, and give the final summary (win rates with CIs,
   p-value, training times, sample efficiency, files, test count, lines of Python). Do
   not merge into main.

## In progress

Nothing. All milestones are finished. A fresh virtual environment install passed lint, all 333 tests, and `reproduce_all.py --quick`.

## Next steps

2. The owner makes the repo public, never Claude.
3. Ideas left open: reward capped wins less, test against unseen strategies, repeat
   training with more seeds.

## Machine facts (checked 2026-11-06)

- Windows 11, 24 logical cores, NVIDIA RTX 5070 Ti Laptop GPU (12 GB).
- Python 3.14.7 is the only installed interpreter. Node is not installed.
- PyTorch 2.11.0+cu128 installed, and `torch.cuda.is_available()` is True.
- `gh` is logged in as DhemanthN with `repo` and `workflow` scopes.
- **Windows Smart App Control is On.** See known issues.

## Decisions

- **DQN comparison (branch `feat/dqn`, 2026-11-08).** Double DQN with dueling heads in
  `rl/dqn.py`, trained like the `two_player` PPO run (same curriculum, opponents, budget,
  shaping, seed). The decisions are below, with details in `docs/rl.md`.
  - No hyperparameter search on Saltmarket, to match PPO. Defaults: n-step 8, batch 512,
    buffer 500k, replay ratio 4, target refresh every 250 gradient steps, epsilon 1.0 to
    0.02 over 10%.
  - Attempt 1 stalled. The value head started at about 0.7 and the target refreshed only
    every 2,000 steps. It was stopped at 4.1M decisions, and its log and checkpoint were
    renamed `_attempt1`, not deleted. Attempt 2 fixes both settings and is the reported run.
  - CartPole training rewards are scaled by 0.01 so Q lies in [0, 1], the same range as
    Saltmarket.
  - The DQN exports as `PolicyWeights` (trunk plus advantage head), so `evaluate.py` and
    `NumpyPolicy.greedy` run it unchanged. `evaluate.py` gained `--label`, default `ppo`.
  - DQN self-play snapshots play epsilon-greedy at 0.05.
  - `sample_opponents` takes a snapshot factory, and `train.py` exposes `append_log` and
    `episode_stats`. PPO behavior is unchanged.
  - The significance test is unpaired, though both agents saw the same seeds, so it is
    slightly conservative.
  - Sample efficiency uses training-log win rates, since no intermediate PPO weights
    were saved.
  - A CartPole trial was stopped early to keep the CPU free during the timed run.

- **Final agents:** `two_player` is quoted for 2 players (85.6% on fresh seeds) and `main`
  for 4 players (40.7%). `two_player` was not retrained after evaluation. Only two runs
  exist, and option 1 (reward change) was not tried, because the owner chose option 2.
- **Fresh seeds:** final numbers use `--fresh-seeds`, which played no part in comparing runs.
- **Removed seaborn:** it was in the planned stack, but no code used it.
- **Output paths:** `SALTMARKET_OUTPUT` redirects outputs, so `--quick` cannot touch real
  results.
- **Measured auction prices replace the earlier probe.** `balanced` also pays about 16% of
  list price at 2 players, so cheap auctions are not unique to `auction_sniper`. It just
  wins about twice as many.
- **Original game instead of Monopoly.** Claude does not build recreations of a
  specific existing game, so the owner approved an original game with the same kinds
  of mechanics. See the originality rule in `CLAUDE.md`.
- **Name and theme:** Saltmarket, an island-trading game. Package `saltmarket`, repo
  `saltmarket-ai`. The local folder stays `monopoly-ai` unless the owner renames it.
- **Terms:** Brig is the jail, Press Gang sends you there, Calm Waters is the rest
  space, depots are houses, ports are hotels, Tide and Ledger are the card decks.
- **Sanity check:** an exact Markov chain landing distribution replaces the comparison
  to published Monopoly landing frequencies.
- **Python 3.12+ instead of 3.11+:** the pinned NumPy 2.5.4 requires 3.12.
- **CI uses CPU PyTorch and skips `slow` tests.** Local runs use the full suite.
- **Auctions are one-shot proxy bids.** Each player submits a limit and the winner pays
  one increment over the runner-up, which matches an ascending auction but needs one
  decision per player. This suits the bots and the RL action space.
- **`sell_group` action:** sells a whole group at once. It guarantees a debtor can always
  liquidate, even when a depot shortage blocks selling a port level by level.
- **Forced liquidation:** if a strategy does not raise enough cash, the engine finishes
  the job in a fixed order, so nobody goes bankrupt while able to pay.
- **Mortgaged transfers:** the receiver pays 10% interest at once and the space stays
  mortgaged. Lifting it later costs the full interest again.
- **Ferry and utility rent** count mortgaged ones the owner holds.
- **Simplification:** no auction for the last depots during a shortage. First to build
  gets them. Record this as a limitation in `RESULTS.md`.
- **Dedicated GPU required by default.** `scripts/train.py --device` defaults to `cuda`,
  which is the RTX 5070 Ti, and errors if CUDA is missing. Game simulation stays on the
  CPU because it is branching Python, and batch-size-one inference gains nothing on a GPU.
- **Group completion counts only when earned** by purchase, auction, or trade. Bankruptcy
  inheritance is excluded, because the winner inherits nearly everything as a game ends.
- **Ratings use a Bradley-Terry fit** on the Elo scale rather than running Elo updates, so
  they do not depend on game order. `never_buy` has no wins, so its rating depends on the
  smoothing term and should be read as "lowest", not as an exact number.
- **CSV instead of Parquet** for raw games: `pyarrow` is not installed, and adding a
  compiled package risks more Smart App Control blocks.
- **RL integration:** `Game` calls strategy hooks synchronously, so `SaltmarketEnv` runs
  each game on a worker thread and hands off at each decision. See `docs/rl.md`.
- **Owner approval for M5:** after the M4 gate the owner wrote "continue when the
  tournament finishes". The tournament had finished, so this was taken as go-ahead.

## Known bugs and open questions

- **The 90% target was not met.** Best result is 85.6% at 2 players. See `RESULTS.md`.
- **Stalemates (owner decided: keep the rules, report both).** Every win rate is reported
  over all games and over decided games only, with the cap rate per bot. Measured figures
  are in `results/tournament_summary.json`. These replace the earlier exploratory probe.
- **`auction_sniper` is strong at 2 players and weak at 4.** A probe (not saved to
  `results/`) showed it pays about 20-26% of list price at 2 players because opponents
  spend down to their cash floor and cannot bid. This is a real effect of the auction
  rules, not a bug. Save a measured version in M6 before quoting it in `RESULTS.md`.
- **Reef looks overpowered:** highest rent per coin spent at both table sizes. This is a
  game balance property of the board, and worth noting in `RESULTS.md`.
- **`expert` is not the best heuristic.** Do not tune it to change this.
- **Smart App Control** blocked two pandas files once each on 2026-11-06:
  `tslib.cp314-win_amd64.pyd` and `window\indexers.cp314-win_amd64.pyd`. Both loaded on
  later runs, with no new blocks since. Cause not confirmed. Do not disable it or work
  around it. If a block recurs, stop and tell the owner. New compiled packages may
  trigger this, so expect it when adding dependencies.
- The palette validator was not run because Node is not installed. The chart uses the
  first two slots of the documented, pre-validated palette.

## Owner feedback log

| Request | Status |
| --- | --- |
| Use an original game rather than recreating Monopoly | Done |
| Keep the rules and report win rates with and without capped games | Done |
| M5 option 2: train a 2-player specialist | Done |
| Run GPU work on the RTX 5070 Ti, not the integrated GPU, now and in future | Done |
| Skip review gates through M5, M6, M7, and the resume update, log decisions here, and give one final summary. Stop only for a blocker, two failed attempts, or a Smart App Control block | Active |
| Remove the accidentally committed `Claude outputs/` folder and ignore it (files not read). It still exists in earlier commits, and only a history rewrite, which the owner decides on, would remove it | Done |
| Add a DQN agent and compare it fairly with PPO, on branch `feat/dqn`, without merging to main | Paused at 10.24M of 20M training decisions, see Paused |
| Pause cleanly for the day: checkpoint, stop everything, commit, update this file | Done |
