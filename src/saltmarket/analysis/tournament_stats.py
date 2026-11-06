"""Statistics over tournament results: win rates, head-to-head, ratings, and group value."""

import math
from pathlib import Path

import numpy as np
import pandas as pd

Z_95 = 1.959963984540054
RATING_CENTER = 1500.0
RATING_SCALE = 400.0
RATING_SMOOTHING = 0.5


def wilson_interval(wins: int, games: int, z: float = Z_95) -> tuple[float, float]:
    """Return the Wilson score interval for a win rate."""
    if games == 0:
        return 0.0, 1.0
    rate = wins / games
    denominator = 1 + z * z / games
    center = (rate + z * z / (2 * games)) / denominator
    margin = z * math.sqrt(rate * (1 - rate) / games + z * z / (4 * games * games)) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def load_rows(directory: Path) -> pd.DataFrame:
    """Load every finished chunk of a tournament, one row per player per game."""
    frames = [
        pd.read_csv(path, keep_default_na=False, dtype={"groups_completed": str})
        for path in sorted(directory.glob("chunk_*.csv"))
    ]
    return pd.concat(frames, ignore_index=True)


def load_group_totals(directory: Path) -> pd.DataFrame:
    """Sum rent, spending, and completions by island group across all chunks."""
    frames = [pd.read_csv(path) for path in sorted(directory.glob("groups_*.csv"))]
    return pd.concat(frames).groupby("group", as_index=False).sum()


def _rate_columns(frame: pd.DataFrame, prefix: str) -> dict[str, object]:
    wins, games = int(frame["won"].sum()), len(frame)
    low, high = wilson_interval(wins, games)
    return {
        f"{prefix}games": games,
        f"{prefix}wins": wins,
        f"{prefix}win_rate": wins / games if games else float("nan"),
        f"{prefix}ci_low": low,
        f"{prefix}ci_high": high,
    }


def win_rates(rows: pd.DataFrame) -> pd.DataFrame:
    """Return per-bot win rates over all games and over decided games only.

    A decided game ended in bankruptcy rather than at the turn cap, where the winner is
    just the richest player.
    """
    records = []
    for bot, frame in rows.groupby("bot"):
        decided = frame[frame["hit_cap"] == 0]
        records.append(
            {
                "bot": bot,
                **_rate_columns(frame, ""),
                **_rate_columns(decided, "decided_"),
                "cap_rate": frame["hit_cap"].mean(),
                "mean_turns": frame["turns"].mean(),
                "bankrupt_rate": (frame["bankrupt_cause"] != "").mean(),
            }
        )
    return pd.DataFrame(records).sort_values("win_rate", ascending=False, ignore_index=True)


def head_to_head(rows: pd.DataFrame) -> pd.DataFrame:
    """Return a matrix of each row bot's win rate against each column bot (2-player games)."""
    first = rows[rows["seat"] == 0].set_index("game_id")
    second = rows[rows["seat"] == 1].set_index("game_id")
    pairs = pd.DataFrame({"a": first["bot"], "b": second["bot"], "a_won": first["won"]})
    mirrored = pd.DataFrame({"a": pairs["b"], "b": pairs["a"], "a_won": 1 - pairs["a_won"]})
    both = pd.concat([pairs, mirrored])
    return both.pivot_table(index="a", columns="b", values="a_won", aggfunc="mean")


def bradley_terry_ratings(rows: pd.DataFrame, iterations: int = 2000) -> pd.Series:
    """Fit Elo-scale ratings to 2-player results with the Bradley-Terry model.

    Unlike running Elo updates, the fit does not depend on game order. A small smoothing
    term keeps a bot with no wins against someone at a finite rating.
    """
    first = rows[rows["seat"] == 0].set_index("game_id")
    second = rows[rows["seat"] == 1].set_index("game_id")
    bots = sorted(set(first["bot"]) | set(second["bot"]))
    position = {bot: i for i, bot in enumerate(bots)}
    size = len(bots)
    wins = np.full((size, size), RATING_SMOOTHING)
    np.fill_diagonal(wins, 0)
    for a, b, a_won in zip(first["bot"], second["bot"], first["won"], strict=True):
        winner, loser = (a, b) if a_won else (b, a)
        wins[position[winner], position[loser]] += 1
    played = wins + wins.T
    strength = np.ones(size)
    for _ in range(iterations):
        denominator = (played / (strength[:, None] + strength[None, :])).sum(axis=1)
        strength = wins.sum(axis=1) / denominator
        strength /= np.exp(np.log(strength).mean())
    ratings = RATING_CENTER + RATING_SCALE * np.log10(strength)
    return pd.Series(ratings, index=bots, name="rating").sort_values(ascending=False)


def game_lengths(rows: pd.DataFrame) -> dict[str, float]:
    """Return length statistics over games, counted in player turns."""
    games = rows.drop_duplicates("game_id")
    decided = games[games["hit_cap"] == 0]
    return {
        "games": len(games),
        "cap_rate": float(games["hit_cap"].mean()),
        "mean_turns": float(games["turns"].mean()),
        "median_turns": float(games["turns"].median()),
        "decided_mean_turns": float(decided["turns"].mean()),
        "decided_median_turns": float(decided["turns"].median()),
    }


def stall_comparison(rows: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Compare capped games with decided games on group completion and building.

    Groups count only if earned by purchase, auction, or trade.
    """
    names = rows["groups_completed"].fillna("")
    earned = names.map(lambda text: len(text.split("|")) if text else 0)
    games = (
        rows.assign(earned=earned)
        .groupby("game_id")
        .agg(earned=("earned", "sum"), peak=("peak_level", "max"), capped=("hit_cap", "max"))
    )
    comparison = {}
    for label, frame in (("capped", games[games["capped"] == 1]),
                         ("decided", games[games["capped"] == 0])):
        comparison[label] = {
            "games": len(frame),
            "share_with_no_group_earned": float((frame["earned"] == 0).mean()),
            "mean_groups_earned": float(frame["earned"].mean()),
            "mean_peak_level": float(frame["peak"].mean()),
        }
    return comparison


def peak_level_win_rates(rows: pd.DataFrame) -> pd.DataFrame:
    """Return win rate by the highest building level a player reached.

    This is an association: players who are already winning can afford to build.
    """
    records = []
    for (size, level), frame in rows.groupby(["table_size", "peak_level"]):
        records.append({"table_size": size, "peak_level": level, **_rate_columns(frame, "")})
    return pd.DataFrame(records)


def seat_win_rates(rows: pd.DataFrame) -> pd.DataFrame:
    """Return the win rate of each seat, as a check that rotation removed seat bias."""
    records = []
    for seat, frame in rows.groupby("seat"):
        records.append({"seat": seat, **_rate_columns(frame, "")})
    return pd.DataFrame(records)


def group_value(rows: pd.DataFrame) -> pd.DataFrame:
    """Compare the win rate of players who completed each group with everyone else.

    This is an association, not proof of cause: strong players complete more groups.
    """
    completed = rows["groups_completed"].fillna("").str.split("|")
    groups = sorted({g for names in completed for g in names if g})
    records = []
    for group in groups:
        has_group = completed.map(lambda names, g=group: g in names)
        holders, others = rows[has_group], rows[~has_group]
        records.append(
            {
                "group": group,
                **_rate_columns(holders, "holder_"),
                "other_win_rate": others["won"].mean(),
                "win_rate_lift": holders["won"].mean() - others["won"].mean(),
            }
        )
    return pd.DataFrame(records).sort_values("win_rate_lift", ascending=False, ignore_index=True)
