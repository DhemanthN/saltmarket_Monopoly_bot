# Handoff

Living progress file. A fresh session should read `CLAUDE.md`, then this file.

## Paused (Session 4, 2026-11-08)

The owner paused Session 4 partway through the v2 task list. Nothing has been pushed.
`main` is 41 commits ahead of `origin/main` (counting this one), the working tree is clean, and every commit
passes ruff and the tests listed below.

### Task list status

| Step | Task | Status |
| --- | --- | --- |
| 1 | Subagent review of the three branches, fixes on each branch | **Done** |
| 2 | Merge feat/perf, feat/new-bots, feat/dqn, docs/v2-roadmap, origin/main | **Done** |
| 3 | 40-bot tournament, 1M+ games | **Partly done**: 2-player finished, 4-player 785 of 2,500 chunks |
| 4 | PPO and DQN evaluation, 1,000 games per opponent, v2 seeds | Not started (code ready and tested) |
| 5 | Regenerate charts, update docs, fact-check subagent | Not started (analyze.py ready) |
| 6 | CHANGELOG [2.0.0] and ROADMAP marked done | Not started |
| 7 | reproduce_all.py (and --quick) end to end, commit | Partly: steps updated and unit-tested, `--quick` not yet run |
| 8 | Remove the three worktrees | Not started. All three still exist |
| 9 | History cleanup with git filter-repo | **Not started.** Only installed `git-filter-repo` into `.venv` |
| 10 | Update docs/RESUME_UPDATE.md | Not started, and needs an owner decision (see below) |

After step 2, the full suite passed 450 tests with 97% coverage, ruff was clean, and the
smoke suite ran in 24.7 s. Later commits added 8 tests, and each targeted test file
passed. Run the full suite again before resuming.

### Run state and how to resume

The 40-bot tournament, `simulate.py --pool all --games-per-pair 2000 --tables 125000`:

- 2-player, `results/raw/round_robin_all/`: 7,800 of 7,800 chunks (1,560,000 games).
- 4-player, `results/raw/tables_all/`: 785 of 2,500 chunks (157,000 of 500,000 games).
  No partial chunk files.
- Summary tables in `results/` are still the v1, 26-bot ones. The script writes them only
  after both phases finish.

Resume in this order. Each command picks up where it stopped:

```powershell
python scripts/simulate.py --pool all --games-per-pair 2000 --tables 125000
python scripts/evaluate.py --run two_player --seed-set v2 --pool all --games-per-bot 1000 --tables 0
python scripts/evaluate.py --run dqn_two_player --seed-set v2 --pool all --games-per-bot 1000 --tables 0 --label dqn
python scripts/evaluate.py --run main --seed-set v2 --pool all --games-per-bot 1000 --tables 5000
python scripts/compare_agents.py --suffix v2_all
python scripts/analyze.py --runs main two_player --best-run two_player --suffix _v2_all --raw-suffix _all --dqn-run dqn_two_player
python scripts/project_stats.py
```

Throughput notes:
- A probe ran 11,800 40-bot games in 33 s. The 2-player phase ran at 700–970 games/s.
- The 4-player phase dropped to about 280 games/s, at times 15. The laptop was on battery
  (discharging, 71%), so keep it plugged in for the rest.
- The first launch hit `BrokenProcessPool` after 10 s. There was no Smart App Control
  event and no error in the application log, so the cause is unknown. A plain rerun
  resumed and worked.

### What the review subagents found, and what was fixed

- **feat/perf** (350 tests pass): no determinism or cache bugs. The golden fingerprints
  were recorded before optimizing, and worker count and chunk size do not change results.
  Fixed in `5013ed3`:
  - removed the unbacked "5,000 games byte for byte" claim
  - softened the cProfile claim and the 24-worker cause
  - derived the pair count instead of hard-coding 325
  - benchmark output now records the baseline commit and the min/max run rates
  - added a chunk-size independence test
- **feat/new-bots** (397 tests pass): no bugs or determinism issues.
  - **Fixed in `91c781c`:**
    - README wording on the 71.2% baseline
    - 34.7% rounded to 34.8%
    - documented the forecast board assumption and the trust-from-ownership assumption
    - fuzz test uses `os.cpu_count()`
  - **Backed by the merge:** the claim that the training bots are unchanged had no test.
    After merging, the perf branch's golden games (all 26 training bots appear in them)
    still match.
  - **Measured and documented:** the reviewer found near-copies.
    - The new `scripts/heldout_overlap.py` saves `results/heldout_overlap.csv`.
    - `cash_reader` plays 71.9% of games exactly like `balanced`, `rival_watcher` 49.8%
      like `group_blocker`, and `leader_denier` 48.7% like `monopoly_trader`.
    - `docs/strategies.md` says so, and `analyze.py` will write `results/heldout_split.csv`,
      with close variants and distinct bots reported separately.
- **feat/dqn** (DQN core correct: Double-DQN target, masking, n-step, terminals). Fixed in
  `4be4763`:
  - The first run stopped at 4.88M decisions, not 4.1M; 4.1M is where it was diagnosed.
  - Removed numbers no file backs: "275 decisions", "Q differed by 0.04", "value 0.71",
    and the CartPole trial scores.
  - Timing claims now quote the training log: median round 1.10 s and 1.33 s, learning
    0.75 and 0.85 s.
  - The unpaired z-test ignored that both agents play the same seeds. `compare.mcnemar_test`
    plus the per-game rows from `evaluate.py` now give a paired test for v2.
  - Left as known nits: resume reseeds workers, so a resumed run is deterministic but not
    identical to an uninterrupted one (now documented). The collector seeds its generator
    and env with the same integer. The replay buffer is saved before `latest.pt`.

### Other decisions this session

- **`docs/RESUME_UPDATE.md` was deleted by the owner** on GitHub on 2026-11-06 (commit
  `4390d76`, merged from origin/main). Task step 10 asks to update it.
  - Proposed: honor the deletion in git and keep the updated file locally, gitignored.
  - **Owner to confirm.** The old version is still in git history and in tag `v1.0.0`.
- **Local tag `v1.0.0`** on `15e5cbf` keeps the 26-bot results easy to find. Not pushed.
- **v2 seed set:** offset 300,000,000 (`rl/evaluate.V2_SEED_OFFSET`). A test checks it
  shares no seed with any earlier evaluation.
- **v2 output names** follow the pattern `rl_eval_*_<run>_v2_all.*`. Per-game rows go to
  `results/raw/eval/` (gitignored).
- **Tournament size:** 2,000 games per pair (780 pairs) plus 125,000 4-player tables in
  all four rotations, 2,060,000 games in all. That is chosen from the probe to fit about
  85 minutes on mains power.
- **Worktrees:** `../monopoly-ai-perf`, `../monopoly-ai-bots`, and `../monopoly-ai-dqn`
  still exist, each clean at its fixed branch tip. Step 8 removes them.
- **History cleanup** (step 9) has not run, so the remote is unchanged:
  `origin https://github.com/DhemanthN/saltmarket-ai.git`.

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

## Held-out bots (branch `feat/new-bots`, 2026-11-08, merged in Session 4)

- 14 new bots in `src/saltmarket/bots/heldout/`, registered in `HELDOUT_BOTS`. `BOTS` is
  still exactly the 26 training bots, so training, the tournament, and `bot_fuzz.csv` are
  unchanged. `bots/registry.make_any_bot` builds either set and is used only by
  evaluation and fuzzing. A test checks no curriculum stage contains a held-out bot.
- `bots/forecast.py`: short-horizon forecasts from the exact Markov chain, used by
  `risk_manager`, `ambush_builder`, `npv_bidder`, and `swap_negotiator`.
- `HeuristicBot` gained `trade_value`, `will_trade_with`, and `premium_for` hooks, and
  `values.spare_mortgages` replaced `AggressiveBuilder`'s inline loop. Hashes of full game
  logs for all 26 training bots were identical before and after.
- Fuzz: 14 × 1,000 debug games at tables drawn from all 40 bots, zero violations
  (`results/bot_fuzz_heldout.csv`, `scripts/fuzz_bots.py --heldout`).
- Evaluation: `scripts/evaluate_heldout.py`, seeds from 9,200,000,000. The `two_player`
  agent won 75.8% (CI 74.7–76.9) of 5,600 games, against 85.6% on the training pool.
  `auction_sniper` on the identical schedule won 71.2%. Hardest bot: `leveraged_buyer`
  at 58.5%. See `RESULTS.md`, "Unseen opponents".
- Decisions: 2-player only, because only the 2-player specialist was asked for and
  the 4-player table draw would mix held-out and training bots. The baseline plays the
  same seeds and seats as the agent, so paired counts are meaningful. Existing results
  and models were not modified.
- Full suite including slow tests: 397 passed (333 before), coverage 98%, ruff clean.
- Not merged into `main`. The owner asked that `Claude outputs/` be removed and ignored.
  It is still present in earlier commits. Rewriting history is the owner's call.

## DQN comparison (branch `feat/dqn`, finished 2026-11-08, merged in Session 4)

Training was paused at 10.24M decisions, resumed from `checkpoints/dqn_two_player/` with
the same command, and finished at 20,008,960 decisions (round 1954, 155,919 gradient
steps, 2,467 s of training time).

- **Result:** DQN won 81.8% of 10,400 fresh-seed 2-player games (CI 81.0–82.5), against
  85.6% for PPO. That is 3.8 points behind (bootstrap CI 2.8–4.7, z = 7.37,
  p = 1.7e-13). DQN ranks 2nd of the 26 bots, behind `auction_sniper`. At 4 players it
  won 17.9%. Full write-up: "PPO vs. DQN" in `RESULTS.md`.
- **New files:** `models/dqn_two_player.npz`, `results/training_log_dqn_two_player.csv`,
  `results/training_log_dqn_two_player_attempt1.csv`, `results/rl_eval_*_dqn_two_player_fresh.*`,
  `results/rl_vs_bots_*_dqn_two_player_fresh.csv`, `results/ppo_vs_dqn.json`,
  `results/ppo_vs_dqn_per_opponent.csv`, `results/ppo_vs_dqn_learning_curves.csv`, and
  `results/figures/ppo_vs_dqn.png`. No existing result or model was changed.
- **Tests:** 368 pass (35 new), ruff is clean, and coverage is 97%. Two torch-heavy DQN
  tests are left out of `smoke` so it stays near 22 s. They still run in the full suite.
- **Checkpoints kept, not committed:** `checkpoints/dqn_two_player/` and
  `checkpoints/dqn_two_player_attempt1/`, about 1.2 GB each. Deleting them is the owner's
  call.
- **Open:** `docs/RESUME_UPDATE.md` still says 333 tests and does not mention DQN. That is
  left for the owner to decide. Merging `feat/dqn` into main is also the owner's call.

## In progress

v2 work, paused. See "Paused (Session 4)" at the top.

## Branch feat/perf (simulator speed, 2026-11-08, merged in Session 4)

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
3. Ideas left open: reward capped wins less, repeat training with more seeds, train with
   some held-out-style bots and test on a further unseen set, and test the 4-player agent
   against unseen bots.

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
- **DQN comparison (branch `feat/dqn`, 2026-11-08).** Double DQN with dueling heads in
  `rl/dqn.py`, trained like the `two_player` PPO run (same curriculum, opponents, budget,
  shaping, seed). The decisions are below, with details in `docs/rl.md`.
  - No hyperparameter search on Saltmarket, to match PPO. Defaults: n-step 8, batch 512,
    buffer 500k, replay ratio 4, target refresh every 250 gradient steps, epsilon 1.0 to
    0.02 over 10%.
  - Attempt 1 stalled. The value head started at about 0.7 and the target refreshed only
    every 2,000 steps. It was diagnosed from its state at 4.1M decisions and stopped at
    4.88M, and its log and checkpoint were renamed `_attempt1`, not deleted. Attempt 2 fixes both settings and is the reported run.
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
| Grow the pool with 14 held-out bots and evaluate the agent against them (2026-11-08) | Done |
| Skip review gates through M5, M6, M7, and the resume update, log decisions here, and give one final summary. Stop only for a blocker, two failed attempts, or a Smart App Control block | Active |
| Remove the accidentally committed `Claude outputs/` folder and ignore it (files not read). It still exists in earlier commits, and only a history rewrite, which the owner decides on, would remove it | Done |
| Add a DQN agent and compare it fairly with PPO, on branch `feat/dqn`, without merging to main | Done, not merged |
| Resume DQN training from the checkpoint and finish the task list | Done |
| Pause cleanly for the day: checkpoint, stop everything, commit, update this file | Done |
