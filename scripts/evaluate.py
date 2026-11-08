"""Evaluate a trained policy on held-out seeds against a bot pool.

Usage: python scripts/evaluate.py --run main --games-per-bot 400 --tables 2500
       python scripts/evaluate.py --run dqn_two_player --seed-set fresh --label dqn
       python scripts/evaluate.py --run two_player --seed-set v2 --pool all --tables 0
Writes results/rl_eval_summary_<suffix>.json and per-opponent CSVs for each table size,
where <suffix> is the run name plus the seed set and pool when they are not the default.
Per-game rows go to results/raw/eval/, so two agents on the same schedule can be paired.
``--tables 0`` skips the 4-player evaluation.
"""

import argparse
import json
import os

import pandas as pd

from saltmarket.bots.catalog import BOTS
from saltmarket.bots.heldout.catalog import HELDOUT_BOTS
from saltmarket.bots.registry import ALL_NAMED_BOTS
from saltmarket.paths import MODELS, RESULTS
from saltmarket.rl import evaluate as ev
from saltmarket.rl.policy import PolicyWeights

POOLS = {"training": BOTS, "heldout": HELDOUT_BOTS, "all": ALL_NAMED_BOTS}
SEED_OFFSETS = {
    "default": 0,
    "fresh": ev.FRESH_SEED_OFFSET,
    "v2": ev.V2_SEED_OFFSET,
}
GAMES_DIR = RESULTS / "raw" / "eval"


def load_weights(run: str) -> PolicyWeights:
    """Load saved weights without importing PyTorch into evaluation workers."""
    from saltmarket.rl.train import load_policy

    return load_policy(MODELS / f"{run}.npz")


def output_suffix(run: str, sample: bool, seed_set: str, pool: str) -> str:
    """Name outputs so that runs, seed sets, and pools never overwrite each other."""
    parts = [run]
    if sample:
        parts.append("sampled")
    if seed_set != "default":
        parts.append(seed_set)
    if pool != "training":
        parts.append(pool)
    return "_".join(parts)


def pool_summaries(frame: pd.DataFrame) -> dict:
    """Split 2-player results into training-bot and held-out-bot opponents."""
    groups = {"training": set(BOTS), "heldout": set(HELDOUT_BOTS)}
    return {
        name: ev.summarize_wins(frame[frame["opponents"].isin(members)])
        for name, members in groups.items()
        if frame["opponents"].isin(members).any()
    }


def main() -> None:
    """Run the evaluations and save the results."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", default="main")
    parser.add_argument("--games-per-bot", type=int, default=400)
    parser.add_argument("--tables", type=int, default=2500)
    parser.add_argument("--sample", action="store_true", help="Sample instead of greedy.")
    parser.add_argument("--seed-set", choices=sorted(SEED_OFFSETS), default="default",
                        help="default was used to compare runs; fresh and v2 were not.")
    parser.add_argument("--pool", choices=sorted(POOLS), default="training")
    parser.add_argument(
        "--label", default=ev.AGENT, help="Name for the agent's row in the bot comparison."
    )
    args = parser.parse_args()

    bots = sorted(POOLS[args.pool])
    weights = load_weights(args.run)
    workers = os.cpu_count() or 1
    greedy = not args.sample
    suffix = output_suffix(args.run, args.sample, args.seed_set, args.pool)
    offset = SEED_OFFSETS[args.seed_set]
    schedules = {"two_player": ev.two_player_schedule(bots, args.games_per_bot, offset)}
    if args.tables > 0:
        schedules["four_player"] = ev.four_player_schedule(bots, args.tables, offset)
    summary: dict = {
        "run": args.run,
        "greedy": greedy,
        "seed_set": args.seed_set,
        "seed_offset": offset,
        "pool": args.pool,
        "bots": len(bots),
        "games_per_bot": args.games_per_bot,
        "tables": args.tables,
    }
    GAMES_DIR.mkdir(parents=True, exist_ok=True)
    for name, schedule in schedules.items():
        frame = ev.run_evaluation(schedule, weights, workers, greedy)
        frame.to_csv(GAMES_DIR / f"rl_games_{name}_{suffix}.csv", index=False)
        table = ev.per_opponent(frame)
        table.to_csv(RESULTS / f"rl_eval_{name}_{suffix}.csv", index=False, float_format="%.5f")
        summary[name] = ev.summarize_wins(frame)
        if name == "two_player":
            summary["two_player_by_pool"] = pool_summaries(frame)
        bots_table = pd.read_csv(RESULTS / f"{name}_win_rates.csv")
        comparison = ev.compare_with_bots(bots_table, summary[name], args.label)
        comparison.to_csv(
            RESULTS / f"rl_vs_bots_{name}_{suffix}.csv", index=False, float_format="%.5f"
        )
    path = RESULTS / f"rl_eval_summary_{suffix}.json"
    path.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
