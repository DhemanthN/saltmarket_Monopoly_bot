"""Evaluate a trained policy, and a baseline bot, against the held-out bots.

Usage: python scripts/evaluate_heldout.py --run two_player --games-per-bot 400
Plays 2-player games against each of the 14 held-out bots, alternating seats, on a
seed range used by no other evaluation. The baseline bot plays the identical schedule,
so both face the same seeds and seats. Writes results/rl_eval_heldout_bots.csv and
results/rl_eval_heldout_bots.json and changes no other file.
"""

import argparse
import json
import os

import pandas as pd

from saltmarket.bots.heldout.catalog import HELDOUT_BOTS
from saltmarket.paths import MODELS, RESULTS
from saltmarket.rl import evaluate as ev
from saltmarket.rl.policy import PolicyWeights

OUTPUT_NAME = "rl_eval_heldout_bots"
TOURNAMENT_WIN_RATES = "two_player_win_rates.csv"


def load_weights(run: str) -> PolicyWeights:
    """Load saved weights without importing PyTorch into evaluation workers."""
    from saltmarket.rl.train import load_policy

    return load_policy(MODELS / f"{run}.npz")


def training_pool_reference(run: str, baseline: str) -> dict:
    """Copy the existing training-pool results for comparison, naming their source files."""
    reference: dict = {}
    summary_path = RESULTS / f"rl_eval_summary_{run}_fresh.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text())
        reference["agent"] = {"source": summary_path.name, **summary["two_player"]}
    rates_path = RESULTS / TOURNAMENT_WIN_RATES
    if rates_path.exists():
        rates = pd.read_csv(rates_path).set_index("bot")
        if baseline in rates.index:
            reference["baseline"] = {"source": rates_path.name, **rates.loc[baseline].to_dict()}
    return reference


def main() -> None:
    """Run both evaluations and save the results."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", default="two_player")
    parser.add_argument("--baseline", default="auction_sniper")
    parser.add_argument("--games-per-bot", type=int, default=400)
    args = parser.parse_args()

    bots = sorted(HELDOUT_BOTS)
    workers = os.cpu_count() or 1
    schedule = ev.two_player_schedule(bots, args.games_per_bot, ev.HELDOUT_SEED_OFFSET)
    frames = {
        "agent": ev.run_evaluation(schedule, load_weights(args.run), workers, greedy=True),
        "baseline": ev.run_evaluation(schedule, None, workers, subject=args.baseline),
    }
    labels = {"agent": f"ppo:{args.run}", "baseline": args.baseline}

    tables = [
        ev.per_opponent(frame).assign(subject=labels[role]) for role, frame in frames.items()
    ]
    table = pd.concat(tables, ignore_index=True)
    table = table[["subject", *(c for c in table.columns if c != "subject")]]
    table.to_csv(RESULTS / f"{OUTPUT_NAME}.csv", index=False, float_format="%.5f")

    summary = {
        "run": args.run,
        "baseline": args.baseline,
        "greedy": True,
        "table_size": 2,
        "games_per_bot": args.games_per_bot,
        "seed_base": ev.EVAL_SEED_BASE + ev.HELDOUT_SEED_OFFSET,
        "opponents": bots,
        "agent": ev.summarize_wins(frames["agent"]),
        "baseline_result": ev.summarize_wins(frames["baseline"]),
        "paired_agent_vs_baseline": ev.paired_outcomes(frames["agent"], frames["baseline"]),
        "training_pool_reference": training_pool_reference(args.run, args.baseline),
    }
    path = RESULTS / f"{OUTPUT_NAME}.json"
    path.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: summary[k] for k in ("agent", "baseline_result")}, indent=2))


if __name__ == "__main__":
    main()
