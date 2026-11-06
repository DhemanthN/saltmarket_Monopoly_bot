# Handoff

Living progress file. A fresh session should read `CLAUDE.md`, then this file.

## Status

| Milestone | Description | Status |
| --- | --- | --- |
| M1 | Project scaffold | Done |
| M2 | Rules engine | Done |
| M3 | Strategy bots (20+) | Done |
| M4 | Monte Carlo tournament | In progress |
| M5 | RL agent (PPO) | Not started |
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
- `src/saltmarket/sim/`: `fuzz.py` and `landing.py`, both parallel with spawn.
- `src/saltmarket/analysis/style.py`: shared chart style.
- `scripts/fuzz.py`, `scripts/fuzz_bots.py`, `scripts/landing_frequency.py`: write to
  `results/`.
- Tests: 242 passed, 99% coverage. `pytest -m smoke` runs 236 tests in about 19 seconds.
- See `git log` for the latest commit.

## In progress

Nothing. Waiting at the M3 review gate.

## Next steps

1. Get owner feedback on M3, including the stalemate question below.
2. M4: build `src/saltmarket/sim/tournament.py` and `scripts/simulate.py`: round-robin and
   random-table tournaments at 2 and 4 players, rotating seats, parallel, resumable.
3. M4: record per-game results including whether the game hit the cap, and report win
   rates with and without capped games.

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
- **RL integration (for M5):** `Game` calls strategy hooks synchronously, so the Gym env
  will need to run the game in a worker thread or restructure the loop. Decide in M5.

## Known bugs and open questions

- **Stalemates (owner decided: keep the rules, report both).** Every win rate is reported
  over all games and over decided games only, with the cap rate per bot. Heuristic tables
  often stall until the turn cap.
  An exploratory 3,000-game probe with random tables (not saved to `results/`, so do not
  quote it in docs) gave cap rates of 3.7%, 16.3%, and 28.8% at 2, 3, and 4 players. Of
  capped games, 71.3% had no completed group, and they averaged 4.2 building levels against
  30.3 in finished games. Spaces get split between players and few bots trade. M4 must
  measure this properly. Capped games are decided by net worth.
- `expert` is not the top bot in the mixed-table fuzz sample. That sample is not a ranking.
  Do not tune `expert` against it. Wait for the M4 tournament.
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
| Keep the rules and report win rates with and without capped games | In progress (M4) |
