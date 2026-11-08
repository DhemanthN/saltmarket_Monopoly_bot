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

## In progress

Nothing. All milestones are finished. A fresh virtual environment install passed lint, all 333 tests, and `reproduce_all.py --quick`.

## Branch feat/perf (simulator speed, 2026-11-08)

- Ownership views (spaces per player, sole owner per group, build sites, split groups)
  are cached in `GameState` and rebuilt only when `state.owner` changes. `owner` is an
  `OwnerList` whose writes bump a version counter.
- `RandomDice` draws faces 512 rolls at a time. NumPy gives the same stream either way,
  which a test checks.
- Bots search only groups they own outright when building, and only split groups when
  proposing trades.
- `run_tournament` plays in-process when `workers == 1` and takes `progress=False`.
- `scripts/fingerprint_games.py` and `tests/data/golden_games.json`: 100 seeded games
  hashed over their full event log, recorded with the engine before optimizing.
  `tests/test_performance.py` replays them. Use `--write` only for intended rule changes.
- `scripts/benchmark.py` writes `results/benchmark.json` and
  `results/figures/benchmark_scaling.png`.
- Measured (`results/benchmark.json`, medians of 3, CPU shared with other sessions):
  2-player 30.9 to 59.6 games/s, 4-player 12.6 to 34.3, best 560 games/s at 16
  workers, about 30 minutes per 1,000,000 games. 350 tests pass, ruff clean.
- Not done here, on purpose: the full tournament was not rerun and no existing result
  file changed. Session 4 reruns it after merging.

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

- **Speed work keeps games bit-for-bit identical.** Checked by 100 golden fingerprints
  recorded with the old engine (`tests/data/golden_games.json`). An earlier note also claimed
  a 5,000-game byte comparison, but no script or file backed it, so review removed it.
- **Benchmark baseline** is the `c59a17c` source exported with `git archive`, timed in
  alternating child processes so both versions see the same machine load. Medians of 3.

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

- **Smoke suite over 30 seconds under load.** On 2026-11-08, with other sessions using
  the CPU, `pytest -m smoke` took 52 s on the old commit and 57 s on feat/perf. Two RL
  tests take most of it. Only the 2-player fingerprint check is in the smoke set.

## Owner feedback log

| Request | Status |
| --- | --- |
| Use an original game rather than recreating Monopoly | Done |
| Keep the rules and report win rates with and without capped games | Done |
| M5 option 2: train a 2-player specialist | Done |
| Run GPU work on the RTX 5070 Ti, not the integrated GPU, now and in future | Done |
| Remove the accidentally committed personal folder and ignore it | Done (still in older commits; rewriting history needs owner approval) |
| Skip review gates through M5, M6, M7, and the resume update, log decisions here, and give one final summary. Stop only for a blocker, two failed attempts, or a Smart App Control block | Active |
