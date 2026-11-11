"""Compare two trained agents on their saved held-out evaluations and training logs.

Usage: python scripts/compare_agents.py --runs two_player dqn_two_player --labels PPO DQN
       python scripts/compare_agents.py --suffix v2_all
Needs results/rl_eval_summary_<run>_<suffix>.json, results/rl_eval_two_player_<run>_<suffix>.csv,
and results/training_log_<run>.csv for both runs. Writes results/<name>.json,
results/<name>_per_opponent.csv, results/<name>_learning_curves.csv, and
results/figures/<name>.png, where <name> defaults to ppo_vs_dqn.

Both agents play the identical schedule, so their games are paired. When the per-game rows
from evaluate.py are in results/raw/eval/, McNemar's paired test is reported alongside the
unpaired z-test and bootstrap. Results are given for all opponents and, when the pool
includes them, for training bots and held-out bots separately.
"""

import argparse
import json

import numpy as np
import pandas as pd

from saltmarket.analysis import compare, plots
from saltmarket.bots.catalog import BOTS
from saltmarket.bots.heldout.catalog import HELDOUT_BOTS
from saltmarket.paths import FIGURES, RESULTS

BIN_STEPS = 500_000
THRESHOLDS = (0.5, 0.6, 0.7, 0.8)
BOOTSTRAP_SEED = 20_261_108
GAMES_DIR = RESULTS / "raw" / "eval"
POOLS = {"all": None, "training": set(BOTS), "heldout": set(HELDOUT_BOTS)}


def _significance(a: pd.DataFrame, b: pd.DataFrame, prefix: str, seed: int) -> dict:
    """Run the z-test and bootstrap on all games (prefix "") or decided games only."""
    def counts(table: pd.DataFrame) -> pd.DataFrame:
        columns = {"opponent": "opponent", f"{prefix}wins": "wins", f"{prefix}games": "games"}
        return table[list(columns)].rename(columns=columns)

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
        "final_bin_win_rate": float(curve["win_rate"].iloc[-1]) if len(curve) else None,
    }


def _paired(runs: list[str], suffix: str, members: set[str] | None) -> dict | None:
    """Pair the two agents' games by game id and run McNemar's test, if rows were saved."""
    paths = [GAMES_DIR / f"rl_games_two_player_{run}_{suffix}.csv" for run in runs]
    if not all(path.exists() for path in paths):
        return None
    frames = [pd.read_csv(path) for path in paths]
    if members is not None:
        frames = [frame[frame["opponents"].isin(members)] for frame in frames]
    a, b = frames
    if not a["game_id"].equals(b["game_id"]) or not a["opponents"].equals(b["opponents"]):
        raise ValueError("The two evaluations did not play the same schedule")
    counts = {
        "games": len(a),
        "both_won": int(((a["won"] == 1) & (b["won"].to_numpy() == 1)).sum()),
        "neither_won": int(((a["won"] == 0) & (b["won"].to_numpy() == 0)).sum()),
    }
    only_a = int(((a["won"] == 1) & (b["won"].to_numpy() == 0)).sum())
    only_b = int(((a["won"] == 0) & (b["won"].to_numpy() == 1)).sum())
    return {**counts, **compare.mcnemar_test(only_a, only_b)}


def _pool_comparison(
    a: pd.DataFrame, b: pd.DataFrame, runs: list[str], suffix: str, pool: str, seed: int
) -> dict:
    """Compare the agents on one pool of opponents, unpaired and paired."""
    members = POOLS[pool]
    if members is not None:
        a, b = a[a["opponent"].isin(members)], b[b["opponent"].isin(members)]
    result = {
        "opponents": len(a),
        "all_games": _significance(a, b, "", seed),
        "decided_games": _significance(a, b, "decided_", seed + 1),
    }
    paired = _paired(runs, suffix, members)
    if paired is not None:
        result["paired_mcnemar"] = paired
    return result


def main() -> None:
    """Compute the comparison and save tables and the chart."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", nargs=2, default=["two_player", "dqn_two_player"])
    parser.add_argument("--labels", nargs=2, default=["PPO", "DQN"])
    parser.add_argument("--suffix", default="fresh", help="Evaluation suffix, such as v2_all.")
    parser.add_argument("--name", default="ppo_vs_dqn")
    args = parser.parse_args()

    pairs = list(zip(args.runs, args.labels, strict=True))
    tables = {
        label: pd.read_csv(RESULTS / f"rl_eval_two_player_{run}_{args.suffix}.csv")
        for run, label in pairs
    }
    logs = {label: pd.read_csv(RESULTS / f"training_log_{run}.csv") for run, label in pairs}
    curves = {label: compare.learning_curve(log, BIN_STEPS) for label, log in logs.items()}
    a, b = tables.values()
    evaluations = {
        label: json.loads((RESULTS / f"rl_eval_summary_{run}_{args.suffix}.json").read_text())
        for run, label in pairs
    }
    pools = [pool for pool, members in POOLS.items()
             if members is None or a["opponent"].isin(members).any()]
    summary = {
        "runs": dict(zip(args.labels, args.runs, strict=True)),
        "evaluation_suffix": args.suffix,
        "difference_is": f"{args.labels[0]} minus {args.labels[1]}",
        "evaluation": {label: data["two_player"] for label, data in evaluations.items()},
        "evaluation_by_pool": {
            label: data.get("two_player_by_pool", {}) for label, data in evaluations.items()
        },
        "pools": {
            pool: _pool_comparison(a, b, args.runs, args.suffix, pool, BOOTSTRAP_SEED + 10 * i)
            for i, pool in enumerate(pools)
        },
        "training": {
            label: _training(logs[label], curves[label]) for label in args.labels
        },
    }
    per_opponent = _per_opponent(a, b, args.labels)
    per_opponent["pool"] = np.where(per_opponent["opponent"].isin(HELDOUT_BOTS), "heldout",
                                    "training")
    significant = per_opponent["p_value"] < 0.05
    summary["opponents_where_better"] = {
        args.labels[0]: int(((per_opponent["difference"] > 0) & significant).sum()),
        args.labels[1]: int(((per_opponent["difference"] < 0) & significant).sum()),
        "note": f"Per-opponent z-tests at p < 0.05, not corrected for {len(per_opponent)} "
                "comparisons.",
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
