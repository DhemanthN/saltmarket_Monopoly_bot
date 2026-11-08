"""Fuzz every strategy at mixed tables and save totals to results/bot_fuzz.csv.

Usage: python scripts/fuzz_bots.py --games 1000
       python scripts/fuzz_bots.py --games 1000 --heldout
``--heldout`` fuzzes the held-out bots at tables drawn from all 40 bots and writes
results/bot_fuzz_heldout.csv instead, so the training-bot file is left alone.
The win column is a quick sanity signal only. Real rankings come from the tournament.
"""

import argparse
import csv
import dataclasses
import os

from saltmarket.bots.heldout.catalog import HELDOUT_BOTS
from saltmarket.bots.registry import ALL_NAMED_BOTS
from saltmarket.paths import RESULTS
from saltmarket.sim.fuzz import BotFuzzSummary, run_bot_fuzz


def main() -> None:
    """Run the fuzz games. Any illegal move or broken invariant stops the run."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--heldout", action="store_true", help="Fuzz the held-out bots.")
    args = parser.parse_args()

    workers = os.cpu_count() or 1
    if args.heldout:
        summaries = run_bot_fuzz(
            args.games, workers, args.seed, names=sorted(HELDOUT_BOTS), pool=sorted(ALL_NAMED_BOTS)
        )
        output = RESULTS / "bot_fuzz_heldout.csv"
    else:
        summaries = run_bot_fuzz(args.games, workers, args.seed)
        output = RESULTS / "bot_fuzz.csv"
    fields = [f.name for f in dataclasses.fields(BotFuzzSummary)]
    RESULTS.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as file:
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
