# Saltmarket AI

Monte Carlo strategy simulator and reinforcement-learning agent for **Saltmarket**,
an original island-trading board game in the roll-and-move property genre.
Portfolio project for a data science freshman: code quality, tests, docs, and honest
results all matter.

## Originality rule (decided with the owner, do not reverse)

Saltmarket is an original game, not a recreation of Monopoly. The name, board, space
names, prices, rent tables, and cards are original designs in `data/board.json` and
`data/cards.json`. Never copy these from an existing game. Genre mechanics are fine:
roll-and-move, buying, auctions, group-based building, a jail equivalent, trading,
bankruptcy. Docs may describe the game as "Monopoly-style", but findings apply to
Saltmarket only and must not be presented as findings about Monopoly.

## Architecture

```
src/saltmarket/
  engine/    board, cards, dice, rules, game state, bank
  bots/      base Strategy class + 20+ strategies
  sim/       tournament runner, Monte Carlo, parallelism
  rl/        gym env, action masking, PPO, training, evaluation
  analysis/  stats + plotting
tests/       pytest + hypothesis
scripts/     CLI entry points: simulate.py, train.py, evaluate.py, analyze.py
data/        board.json, cards.json
results/     summary CSVs, metrics, figures/
docs/        strategies.md, rl.md, RESUME_UPDATE.md
```

## Commands (PowerShell)

```powershell
.\.venv\Scripts\Activate.ps1          # activate environment
pip install -r requirements.txt       # setup: pinned versions, CUDA PyTorch
pip install -e ".[dev]"               # setup: this project, editable
ruff check .                          # lint
pytest -q                             # all tests
pytest -m smoke                       # under 30 seconds
pytest --cov                          # coverage, run before each review gate
python scripts/fuzz.py                # 10,000 random-bot games with invariants
python scripts/landing_frequency.py   # simulation vs exact Markov chain, first chart
python scripts/simulate.py            # tournament (from M4)
python scripts/train.py               # PPO training (from M5)
python scripts/evaluate.py            # held-out evaluation (from M5)
python scripts/analyze.py             # charts and tables (from M6)
```

## Rules

- Windows and PowerShell. Multiprocessing sits behind `if __name__ == "__main__":`
  and uses the spawn start method.
- All randomness uses a seeded `numpy.random.Generator` passed in explicitly. Same
  seed gives the identical game. No global random calls.
- Never invent, estimate, or hard-code results. Every number in docs or charts comes
  from a script that was actually run and saved to `results/`.
- Code must run on CPU as well as CUDA.
- If something is ambiguous or seems wrong, ask the owner instead of guessing.
- Data-driven rules: prefer JSON and config dataclasses over if/else chains and
  magic numbers.

## Code conventions

Small readable modules, type hints everywhere, docstrings on public functions, no dead
code or commented-out blocks. It should read like strong intern code to a hiring
engineer.

## Testing

- Write tests alongside code. After each meaningful change run `ruff check .` and
  `pytest -q`, and fix failures before new features.
- Bug fix: add a reproducing test first.
- Never delete or weaken a test without telling the owner why.
- Keep `pytest -m smoke` under 30 seconds.
- Before each review gate, run the full suite and report pass count and coverage.

## Git

- Private repo `DhemanthN/saltmarket-ai`. The owner makes it public, never Claude.
- Commit after every tested sub-step with conventional messages (`feat:`, `fix:`,
  `test:`, `docs:`). Push at the end of each milestone. Never commit failing tests.
- Do not commit `.venv`, caches, checkpoints over about 50 MB, or raw simulation
  dumps. Keep small summary CSVs and final charts.

## Session workflow

- `HANDOFF.md` is the living progress file. Update it and commit at the end of every
  milestone and major sub-step.
- If the conversation gets long, context is compacted, or usage runs low: stop new
  work, update `HANDOFF.md` in detail, commit, push, and tell the owner to start a
  new session.
- At each review gate: stop, summarize in plain language, show test results and sample
  output, list decisions, explain key concepts simply (the owner is a freshman with
  basic Python and little ML experience), then wait for feedback.
- Owner feedback is top priority. Log it in `HANDOFF.md`.
- If an approach fails after two genuine attempts, record it in `HANDOFF.md` and ask.
- Give the expected runtime before starting anything over about 30 minutes. Training
  must be resumable from checkpoints.
- Final deliverable `docs/RESUME_UPDATE.md` reports real measured numbers only. The
  resume must never claim anything the repo does not back up.
