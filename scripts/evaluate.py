"""Evaluate a trained policy on held-out seeds against the full bot pool.

Usage: python scripts/evaluate.py --run main --games-per-bot 400 --tables 2500
Writes results/rl_eval_summary_<run>.json and per-opponent CSVs for each table size.
"""

import argparse
import json
import os
from pathlib import Path

import pandas as pd

from saltmarket.bots.catalog import BOTS
from saltmarket.rl import evaluate as ev
from saltmarket.rl.policy import PolicyWeights

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def load_weights(run: str) -> PolicyWeights:
    """Load saved weights without importing PyTorch into evaluation workers."""
    from saltmarket.rl.train import load_policy

    return load_policy(ROOT / "models" / f"{run}.npz")


def main() -> None:
    """Run both evaluations and save the results."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", default="main")
    parser.add_argument("--games-per-bot", type=int, default=400)
    parser.add_argument("--tables", type=int, default=2500)
    parser.add_argument("--sample", action="store_true", help="Sample instead of greedy.")
    args = parser.parse_args()

    bots = sorted(BOTS)
    weights = load_weights(args.run)
    workers = os.cpu_count() or 1
    greedy = not args.sample
    suffix = f"{args.run}_sampled" if args.sample else args.run
    schedules = {
        "two_player": ev.two_player_schedule(bots, args.games_per_bot),
        "four_player": ev.four_player_schedule(bots, args.tables),
    }
    summary: dict = {"run": args.run, "greedy": greedy}
    for name, schedule in schedules.items():
        frame = ev.run_evaluation(schedule, weights, workers, greedy)
        table = ev.per_opponent(frame)
        table.to_csv(RESULTS / f"rl_eval_{name}_{suffix}.csv", index=False, float_format="%.5f")
        summary[name] = ev.summarize_wins(frame)
        bots_table = pd.read_csv(RESULTS / f"{name}_win_rates.csv")
        comparison = ev.compare_with_bots(bots_table, summary[name], ev.AGENT)
        comparison.to_csv(
            RESULTS / f"rl_vs_bots_{name}_{suffix}.csv", index=False, float_format="%.5f"
        )
    path = RESULTS / f"rl_eval_summary_{suffix}.json"
    path.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
