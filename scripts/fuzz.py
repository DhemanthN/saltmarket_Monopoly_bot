"""Run the random-bot fuzz test and save its totals to results/fuzz_summary.json.

Usage: python scripts/fuzz.py --games 10000
"""

import argparse
import json
import os
from pathlib import Path

from saltmarket.sim.fuzz import run_fuzz

RESULTS = Path(__file__).resolve().parents[1] / "results"


def main() -> None:
    """Run the fuzz games. Any illegal move or broken invariant stops the run."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    result = run_fuzz(args.games, os.cpu_count() or 1, args.seed)
    summary = {
        "games": result.games,
        "first_seed": args.seed,
        "total_turns": result.turns,
        "mean_turns": result.turns / result.games,
        "games_hitting_turn_cap": result.hit_cap,
        "exceptions": 0,
        "invariant_violations": 0,
    }
    (RESULTS / "fuzz_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
