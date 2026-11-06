"""Create every chart and analysis table from saved results.

Usage: python scripts/analyze.py --runs main two_player --best-run two_player
Needs results/raw/ from simulate.py and saved models and evaluations from train.py and
evaluate.py. The first run listed is used for 4-player charts.
"""

import argparse
import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

import pandas as pd

from saltmarket.analysis import plots
from saltmarket.analysis import tournament_stats as stats
from saltmarket.analysis.tendencies import auction_prices, measure_tendencies
from saltmarket.bots.catalog import make_bot
from saltmarket.rl.agent import AgentStrategy
from saltmarket.rl.policy import NumpyPolicy, PolicyWeights

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
FIGURES = RESULTS / "figures"
TENDENCY_GAMES = 2600
AUCTION_GAMES = 2000
ANALYSIS_SEED = 5_000_000_000


def make_agent(weights: PolicyWeights) -> AgentStrategy:
    """Create a greedy agent from saved weights."""
    return AgentStrategy(NumpyPolicy(weights).greedy)


def _tendencies(task: tuple) -> pd.DataFrame:
    label, weights, bot = task
    maker = partial(make_agent, weights) if weights is not None else partial(make_bot, bot)
    return measure_tendencies(maker, label, TENDENCY_GAMES, ANALYSIS_SEED)


def _auction(task: tuple[str, int]) -> dict:
    return auction_prices(task[0], task[1], AUCTION_GAMES, ANALYSIS_SEED + 1_000_000)


def behavior_tables(weights: PolicyWeights, best_bot: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Measure the agent's habits and auction prices, in parallel."""
    context = multiprocessing.get_context("spawn")
    workers = os.cpu_count() or 1
    with ProcessPoolExecutor(max_workers=workers, mp_context=context) as pool:
        habits = pool.map(_tendencies, [("PPO agent", weights, None), (best_bot, None, best_bot)])
        tasks = [(best_bot, 2), (best_bot, 4), ("balanced", 2), ("balanced", 4)]
        prices = pool.map(_auction, tasks)
        return pd.concat(list(habits), ignore_index=True), pd.DataFrame(list(prices))


def main() -> None:
    """Build all tables and charts."""
    from saltmarket.rl.train import load_policy

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", nargs="+", default=["main"])
    parser.add_argument("--best-run", default="main", help="Run shown in 2-player charts.")
    args = parser.parse_args()
    FIGURES.mkdir(parents=True, exist_ok=True)

    two_rows = stats.load_rows(RESULTS / "raw" / "round_robin")
    four_rows = stats.load_rows(RESULTS / "raw" / "tables")
    levels = pd.concat(
        [stats.peak_level_win_rates(two_rows), stats.peak_level_win_rates(four_rows)],
        ignore_index=True,
    )
    levels.to_csv(RESULTS / "peak_level_win_rates.csv", index=False, float_format="%.5f")

    two_table = pd.read_csv(RESULTS / f"rl_vs_bots_two_player_{args.best_run}.csv")
    four_table = pd.read_csv(RESULTS / f"rl_vs_bots_four_player_{args.runs[0]}.csv")
    best_bot = pd.read_csv(RESULTS / "two_player_win_rates.csv").iloc[0]["bot"]
    weights = load_policy(ROOT / "models" / f"{args.best_run}.npz")
    tendencies, prices = behavior_tables(weights, best_bot)
    tendencies.to_csv(RESULTS / "rl_tendencies.csv", index=False, float_format="%.5f")
    prices.to_csv(RESULTS / "auction_prices.csv", index=False, float_format="%.5f")

    landing = pd.read_csv(RESULTS / "landing_frequency.csv")
    plots.board_heatmap(landing, FIGURES / "board_heatmap.png")
    plots.ranked_win_rates(two_table, four_table, FIGURES / "win_rates.png")
    plots.head_to_head_heatmap(
        pd.read_csv(RESULTS / "head_to_head.csv", index_col=0), FIGURES / "head_to_head.png"
    )
    plots.ratings_leaderboard(pd.read_csv(RESULTS / "ratings.csv"), FIGURES / "ratings.png")
    plots.game_length_distribution(two_rows, four_rows, FIGURES / "game_length.png")
    plots.group_roi(
        pd.read_csv(RESULTS / "two_player_group_economics.csv"),
        pd.read_csv(RESULTS / "four_player_group_economics.csv"),
        FIGURES / "group_roi.png",
    )
    plots.building_level_effect(levels, FIGURES / "building_level.png")
    logs = {run: pd.read_csv(RESULTS / f"training_log_{run}.csv") for run in args.runs}
    plots.training_curves(logs, FIGURES / "training_curves.png")
    plots.agent_vs_opponents(
        pd.read_csv(RESULTS / f"rl_eval_two_player_{args.best_run}.csv"),
        FIGURES / "agent_vs_opponents.png",
        "PPO agent against each bot, 2 players",
    )
    plots.tendencies_chart(tendencies, FIGURES / "agent_tendencies.png")


if __name__ == "__main__":
    main()
