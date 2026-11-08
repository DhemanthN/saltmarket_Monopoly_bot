"""Statistics for comparing two agents: significance tests and learning curves."""

import math

import numpy as np
import pandas as pd


def two_proportion_z_test(
    wins_a: int, games_a: int, wins_b: int, games_b: int
) -> dict[str, float]:
    """Test whether two win rates differ, using the pooled two-proportion z-test.

    Returns the difference (a minus b), the z statistic, and the two-sided p-value.
    """
    rate_a, rate_b = wins_a / games_a, wins_b / games_b
    pooled = (wins_a + wins_b) / (games_a + games_b)
    spread = math.sqrt(pooled * (1 - pooled) * (1 / games_a + 1 / games_b))
    z = (rate_a - rate_b) / spread if spread else 0.0
    return {"difference": rate_a - rate_b, "z": z, "p_value": math.erfc(abs(z) / math.sqrt(2))}


def bootstrap_difference(
    a: pd.DataFrame,
    b: pd.DataFrame,
    rng: np.random.Generator,
    replicates: int = 10_000,
    level: float = 0.95,
) -> dict[str, float]:
    """Return a percentile bootstrap interval for the win-rate difference (a minus b).

    ``a`` and ``b`` hold ``opponent``, ``wins``, and ``games`` columns. The schedule fixes
    how many games each opponent gets, so games are resampled within each opponent.
    Resampling n win-or-loss outcomes with replacement gives a binomial count, so each
    replicate draws one binomial per agent and opponent.
    """
    merged = a.merge(b, on="opponent", suffixes=("_a", "_b"))
    if len(merged) != len(a) or len(merged) != len(b):
        raise ValueError("Both tables must cover the same opponents")
    differences = []
    for side in ("a", "b"):
        games = merged[f"games_{side}"].to_numpy()
        rates = merged[f"wins_{side}"].to_numpy() / games
        draws = rng.binomial(games, rates, size=(replicates, len(merged)))
        differences.append(draws.sum(axis=1) / games.sum())
    replicate_differences = differences[0] - differences[1]
    tail = (1 - level) / 2
    low, high = np.quantile(replicate_differences, [tail, 1 - tail])
    observed = merged["wins_a"].sum() / merged["games_a"].sum()
    observed -= merged["wins_b"].sum() / merged["games_b"].sum()
    return {"difference": float(observed), "ci_low": float(low), "ci_high": float(high)}


def learning_curve(log: pd.DataFrame, bin_steps: int) -> pd.DataFrame:
    """Pool a training log into bins of ``bin_steps`` decisions.

    Each bin's win rate counts every game that finished in it, so rows with more games
    weigh more. ``steps`` is the end of the bin.
    """
    wins = (log["win_rate"].fillna(0) * log["episodes"]).round()
    bins = (log["steps"] - 1) // bin_steps
    grouped = pd.DataFrame({"bin": bins, "wins": wins, "episodes": log["episodes"]})
    pooled = grouped.groupby("bin", as_index=False)[["wins", "episodes"]].sum()
    stages = log.groupby(bins)["stage"].last().to_numpy()
    return pd.DataFrame(
        {
            "steps": (pooled["bin"] + 1) * bin_steps,
            "stage": stages,
            "episodes": pooled["episodes"].astype(int),
            "win_rate": pooled["wins"] / pooled["episodes"].where(pooled["episodes"] > 0),
        }
    )


def stage_win_rates(log: pd.DataFrame) -> pd.Series:
    """Return the pooled training win rate in each curriculum stage, in stage order."""
    wins = (log["win_rate"].fillna(0) * log["episodes"]).round()
    frame = pd.DataFrame({"stage": log["stage"], "wins": wins, "episodes": log["episodes"]})
    totals = frame.groupby("stage", sort=False)[["wins", "episodes"]].sum()
    return totals["wins"] / totals["episodes"]


def steps_to_reach(curve: pd.DataFrame, threshold: float, after: int = 0) -> int | None:
    """Return the end of the first bin past ``after`` that reaches ``threshold``.

    Returns None if the curve never gets there.
    """
    reached = curve[(curve["steps"] > after) & (curve["win_rate"] >= threshold)]
    return int(reached["steps"].iloc[0]) if len(reached) else None
