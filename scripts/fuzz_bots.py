"""Fuzz every strategy at mixed tables and save totals to results/bot_fuzz.csv.

Usage: python scripts/fuzz_bots.py --games 1000
The win column is a quick sanity signal only. Real rankings come from the tournament.
"""

import argparse
import csv
import dataclasses
import os
from pathlib import Path

from saltmarket.sim.fuzz import BotFuzzSummary, run_bot_fuzz

RESULTS = Path(__file__).resolve().parents[1] / "results"


def main() -> None:
    """Run the fuzz games. Any illegal move or broken invariant stops the run."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    summaries = run_bot_fuzz(args.games, os.cpu_count() or 1, args.seed)
    fields = [f.name for f in dataclasses.fields(BotFuzzSummary)]
    with (RESULTS / "bot_fuzz.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(fields)
        writer.writerows(dataclasses.astuple(s) for s in summaries)
    for summary in sorted(summaries, key=lambda s: -s.wins):
        print(
            f"{summary.name:24} games={summary.games} wins={summary.wins:4} "
            f"cap={summary.hit_cap:4} mean_turns={summary.turns / summary.games:6.0f}"
        )


if __name__ == "__main__":
    main()
