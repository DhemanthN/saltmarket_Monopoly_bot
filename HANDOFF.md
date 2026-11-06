# Handoff

Living progress file. A fresh session should read `CLAUDE.md`, then this file.

## Status

| Milestone | Description | Status |
| --- | --- | --- |
| M1 | Project scaffold | Done, awaiting owner review |
| M2 | Rules engine | Not started |
| M3 | Strategy bots (20+) | Not started |
| M4 | Monte Carlo tournament | Not started |
| M5 | RL agent (PPO) | Not started |
| M6 | Data analysis and charts | Not started |
| M7 | Documentation and polish | Not started |
| Final | `docs/RESUME_UPDATE.md` | Not started |

## Done so far

- `CLAUDE.md`, `HANDOFF.md`: session memory.
- `pyproject.toml`: pinned dependencies, ruff, pytest, and coverage config.
- `requirements.txt`: full `pip freeze` with the CUDA PyTorch index URL.
- `.gitignore`, `LICENSE` (MIT), `README.md` (placeholder until M7).
- `.github/workflows/ci.yml`: ruff and non-slow pytest on push, using CPU PyTorch.
- `src/saltmarket/`: empty subpackages `engine`, `bots`, `sim`, `rl`, `analysis`.
- `tests/test_scaffold.py`: 6 smoke tests that check the package imports.
- `scripts/`, `data/`, `results/figures/`, `docs/`: empty, held by `.gitkeep`.
- Tests: 6 passed. See `git log` for the latest commit.

## In progress

Nothing. Waiting at the M1 review gate.

## Next steps

1. Get owner feedback on M1.
2. M2: design the original 40-space board in `data/board.json` and the 32 cards in
   `data/cards.json`. Follow the originality rule in `CLAUDE.md`.
3. M2: build `src/saltmarket/engine/` with tests alongside each rule.

## Machine facts (checked 2026-11-06)

- Windows 11, 24 logical cores, NVIDIA RTX 5070 Ti Laptop GPU (12 GB).
- Python 3.14.7 is the only installed interpreter.
- PyTorch 2.11.0+cu128 installed, and `torch.cuda.is_available()` is True.
- `gh` is logged in as DhemanthN with `repo` and `workflow` scopes.

## Decisions

- **Original game instead of Monopoly.** Claude does not build recreations of a
  specific existing game, so the owner approved an original game with the same kinds
  of mechanics. See the originality rule in `CLAUDE.md`.
- **Name and theme:** Saltmarket, an island-trading game. Package `saltmarket`, repo
  `saltmarket-ai`. The local folder stays `monopoly-ai` unless the owner renames it.
- **Sanity check:** an exact Markov chain landing distribution replaces the comparison
  to published Monopoly landing frequencies.
- **Python 3.12+ instead of 3.11+:** the pinned NumPy 2.5.4 requires 3.12.
- **CI uses CPU PyTorch and skips `slow` tests** to keep runs short. Local runs use
  CUDA and the full suite.

## Known bugs and open questions

None yet.

## Owner feedback log

| Request | Status |
| --- | --- |
| Use an original game rather than recreating Monopoly | Accepted, in progress |
