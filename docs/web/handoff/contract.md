# Handoff: contract

Branch: `contract` · Date: 2026-11-23 · Status: done

## What changed
- `src/saltmarket/web/`: `contract.py` (dataclasses, source of truth), `labels.py` (action id to labelled choice), `seats.py` (`HumanSeat`, `AgentSeat`, `make_seat`), `observed.py` (`ObservedGame`, a `Game` subclass that narrates events), `session.py` (`GameSession`), `export_ts.py` (TypeScript writer).
- `scripts/export_contract.py` writes `web/src/contract/types.ts` (`--check` fails on drift). `scripts/record_fixtures.py` writes 5 games to `web/fixtures/` plus `index.json`.
- Refactors, no behaviour change: `load_policy`/`save_policy` moved from `rl/train.py` to `rl/policy.py` (torch-free; callers updated); `NumpyPolicy.probabilities` and `.advantages` added; hash code moved from `sim/fingerprint.py` to `sim/digest.py` (`game_digest`). No file under `engine/` changed.
- Tests: `tests/test_web_session.py` (14), `tests/test_web_contract.py` (10 incl. drift and fixture replay), `web/src/contract/fixtures.test.ts` (Vitest, 5 games x 3 checks).

## How to verify
```powershell
$env:PYTHONPATH = "<worktree>\src"
ruff check .
pytest -m smoke                       # 421 passed, 28.6 s (was 27.8 s)
pytest -q                             # full suite exit 0
pytest tests/test_web_session.py tests/test_web_contract.py --cov=saltmarket.web   # 98%
python scripts/export_contract.py --check
python scripts/record_fixtures.py     # byte-identical output on re-run
cd web; npx tsc --noEmit; npx vitest run   # 34 passed
```
Fixtures: `vs_ppo_2p` (seed 23), `vs_dqn_2p` (13), `table_4p` (11, human + PPO + 2 bots), `bots_3p` (11, has auctions, an accepted trade, 2 bankruptcies), `watch_2p` (5, no human).

## Decisions made
- **Pause by replay.** Pyodide has no threads. `GameSession` stores the human's answers and rebuilds the seeded game on each `submit`; the event prefix is asserted unchanged. Cost: one game replay per submit. Measured on desktop: a 650-decision game took 115 s in total, with late submits near 0.5 s, and Pyodide is slower. Task 5 should use the spike's blocking path instead: build `HumanSeat(answer)` where `answer` blocks in `Atomics.wait`, run `ObservedGame` once, and stream `events`. Both paths share the same classes.
- **DQN is 2-player only** (owner instruction): `GameSession` raises `ValueError` for `dqn` at any other table size. PPO uses `two_player.npz` at 2 seats and `main.npz` at 3 to 4.
- **Explanations.** Agents play `NumpyPolicy.greedy`. PPO: top 3 legal by probability. DQN: top 3 by Q rebuilt as `V + A - mean_legal(A)`. `value` is the critic (PPO) or V (DQN). `Explanation.model` names the weights file.
- **Extra events beyond the PLAN list**, so `reduceEvents` reproduces the engine's state exactly: `cash` (seat, balance, delta) and `owner` (space, seat or null). `build`, `sell`, `mortgage`, `unmortgage` come from board diffs, so forced liquidations are included. State events always come before the next story event. `amount` on mortgage events is informational only.
- **Naming.** Python fields are snake_case, JSON and TS are camelCase. Every key is always present (`null` instead of optional). `from`/`to` became `payer`/`payee` (rent) and an embedded `offer` with `proposer`/`responder` (trade). `SeatKind` is a plain `string[]` in `SessionConfig`. `LegalAction` has an optional `offer` for trade proposals. `fingerprint()` is `string | null` until the game ends.
- Bots make no `decision` events, only human and agent seats do.

## Left for later / known issues
- Task 5: move the models into the Pyodide bundle at `/app/models` (`paths.MODELS` resolves from the package location). Avoid `sim/tournament` imports (tqdm); `sim/digest.py` already avoids them.
- `HumanSeat` fixtures use a scripted rule (`choose` in `record_fixtures.py`: buy, bid low, build, trade, never sell), so they show a weak human, not typical play.
- The Python reducer test compares cash only for seats that had cash events.
- Full-suite coverage was not run (review gates are off); web package coverage is 98%.
- Pyodide parity of `ObservedGame` was not tested, only desktop.
