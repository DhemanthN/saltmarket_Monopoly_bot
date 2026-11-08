"""Compare two trained agents on their saved fresh-seed evaluations and training logs.

Usage: python scripts/compare_agents.py --runs two_player dqn_two_player --labels PPO DQN
Needs results/rl_eval_summary_<run>_fresh.json, results/rl_eval_two_player_<run>_fresh.csv,
and results/training_log_<run>.csv for both runs. Writes results/<name>.json,
results/<name>_per_opponent.csv, results/<name>_learning_curves.csv, and
results/figures/<name>.png, where <name> defaults to ppo_vs_dqn.
"""

import argparse
import json

import numpy as np
import pandas as pd

from saltmarket.analysis import compare, plots
from saltmarket.paths import FIGURES, RESULTS

BIN_STEPS = 500_000
THRESHOLDS = (0.5, 0.6, 0.7, 0.8)
BOOTSTRAP_SEED = 20_261_108


def _significance(a: pd.DataFrame, b: pd.DataFrame, prefix: str, seed: int) -> dict:
    """Run the z-test and bootstrap on all games (prefix "") or decided games only."""
    def counts(table: pd.DataFrame) -> pd.DataFrame:
        return table.rename(columns={f"{prefix}wins": "wins", f"{prefix}games": "games"})[
            ["opponent", "wins", "games"]
        ]

    a, b = counts(a), counts(b)
    test = compare.two_proportion_z_test(
        int(a["wins"].sum()), int(a["games"].sum()), int(b["wins"].sum()), int(b["games"].sum())
    )
    interval = compare.bootstrap_difference(a, b, np.random.default_rng(seed))
    return {**test, "bootstrap_ci_low": interval["ci_low"],
            "bootstrap_ci_high": interval["ci_high"]}


def _per_opponent(a: pd.DataFrame, b: pd.DataFrame, labels: list[str]) -> pd.DataFrame:
    rows = []
    for (_, left), (_, right) in zip(
        a.sort_values("opponent").iterrows(), b.sort_values("opponent").iterrows(), strict=True
    ):
        test = compare.two_proportion_z_test(
            int(left["wins"]), int(left["games"]), int(right["wins"]), int(right["games"])
        )
        rows.append(
            {
                "opponent": left["opponent"],
                f"{labels[0]}_win_rate": left["win_rate"],
                f"{labels[1]}_win_rate": right["win_rate"],
                "difference": test["difference"],
                "p_value": test["p_value"],
            }
        )
    return pd.DataFrame(rows).sort_values("difference", ignore_index=True)


def _training(log: pd.DataFrame, curve: pd.DataFrame) -> dict:
    stages = compare.stage_win_rates(log)
    return {
        "total_steps": int(log["steps"].iloc[-1]),
        "wall_clock_seconds": float(log["seconds"].iloc[-1]),
        "decisions_per_second": float(log["steps"].iloc[-1] / log["seconds"].iloc[-1]),
        "stage_win_rates": {stage: float(rate) for stage, rate in stages.items()},
        "steps_to_reach": {
            f"{threshold:.0%}": compare.steps_to_reach(curve, threshold) for threshold in THRESHOLDS
        },
        "final_bin_win_rate": float(curve["win_rate"].iloc[-1]),
    }


def main() -> None:
    """Compute the comparison and save tables and the chart."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", nargs=2, default=["two_player", "dqn_two_player"])
    parser.add_argument("--labels", nargs=2, default=["PPO", "DQN"])
    parser.add_argument("--name", default="ppo_vs_dqn")
    args = parser.parse_args()

    tables = {
        label: pd.read_csv(RESULTS / f"rl_eval_two_player_{run}_fresh.csv")
        for run, label in zip(args.runs, args.labels, strict=True)
    }
    logs = {
        label: pd.read_csv(RESULTS / f"training_log_{run}.csv")
        for run, label in zip(args.runs, args.labels, strict=True)
    }
    curves = {label: compare.learning_curve(log, BIN_STEPS) for label, log in logs.items()}
    a, b = tables.values()
    summary = {
        "runs": dict(zip(args.labels, args.runs, strict=True)),
        "difference_is": f"{args.labels[0]} minus {args.labels[1]}",
        "evaluation": {
            label: json.loads((RESULTS / f"rl_eval_summary_{run}_fresh.json").read_text())[
                "two_player"
            ]
            for run, label in zip(args.runs, args.labels, strict=True)
        },
        "all_games": _significance(a, b, "", BOOTSTRAP_SEED),
        "decided_games": _significance(a, b, "decided_", BOOTSTRAP_SEED + 1),
        "training": {
            label: _training(logs[label], curves[label]) for label in args.labels
        },
    }
    per_opponent = _per_opponent(a, b, args.labels)
    summary["opponents_where_better"] = {
        args.labels[0]: int(((per_opponent["difference"] > 0)
                             & (per_opponent["p_value"] < 0.05)).sum()),
        args.labels[1]: int(((per_opponent["difference"] < 0)
                             & (per_opponent["p_value"] < 0.05)).sum()),
        "note": "Per-opponent z-tests at p < 0.05, not corrected for 26 comparisons.",
    }

    per_opponent.to_csv(RESULTS / f"{args.name}_per_opponent.csv", index=False,
                        float_format="%.5f")
    pd.concat([curve.assign(agent=label) for label, curve in curves.items()]).to_csv(
        RESULTS / f"{args.name}_learning_curves.csv", index=False, float_format="%.5f"
    )
    (RESULTS / f"{args.name}.json").write_text(json.dumps(summary, indent=2) + "\n")
    FIGURES.mkdir(parents=True, exist_ok=True)
    plots.agent_comparison(curves, tables, FIGURES / f"{args.name}.png")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
