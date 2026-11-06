# Handoff

Living progress file. A fresh session should read `CLAUDE.md`, then this file.

## Status

| Milestone | Description | Status |
| --- | --- | --- |
| M1 | Project scaffold | Done |
| M2 | Rules engine | Done |
| M3 | Strategy bots (20+) | Done |
| M4 | Monte Carlo tournament | Done |
| M5 | RL agent (PPO) | First run evaluated, awaiting owner review |
| M6 | Data analysis and charts | Not started |
| M7 | Documentation and polish | Not started |
| Final | `docs/RESUME_UPDATE.md` | Not started |

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

Nothing running. Waiting at the M5 review gate. Run `main` is trained and evaluated:
`models/main.npz`, `results/training_log_main.csv`, `results/rl_eval_summary_main.json`,
`results/rl_eval_*_main.csv`, and `results/rl_vs_bots_*_main.csv`.

## Next steps

1. Get the owner's choice on how to continue M5 (options are in the M5 gate summary below).
2. Any new run needs a new `--run` name so run `main` stays intact for comparison.
3. Then M6: charts and `RESULTS.md`. Save a measured version of the `auction_sniper` price
   finding first.

## Machine facts (checked 2026-11-06)

- Windows 11, 24 logical cores, NVIDIA RTX 5070 Ti Laptop GPU (12 GB).
- Python 3.14.7 is the only installed interpreter. Node is not installed.
- PyTorch 2.11.0+cu128 installed, and `torch.cuda.is_available()` is True.
- `gh` is logged in as DhemanthN with `repo` and `workflow` scopes.
- **Windows Smart App Control is On.** See known issues.

## Decisions

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

- **RL run `main` misses the 90% target.** Held-out results: 70.8% at 2 players and 40.8%
  at 4. Against the bots it ranks 4th at 2 players, and 2nd at 4 players but 11th on
  decided games. Its 4-player cap rate is 41.6% against 26.1% for bot tables, and it wins
  46.3% of capped games, so it benefits from stalled games. Training counts a capped win
  the same as a bankruptcy win, which probably encourages this (not yet tested). Curves
  flatten after about 8M steps. Untested ideas: reward capped wins less, raise
  `gae_lambda` for long games, train per table size, train longer.
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
