"""Create every chart and analysis table from saved results.

Usage: python scripts/analyze.py --runs main two_player --best-run two_player --fresh
       python scripts/analyze.py --runs main two_player --best-run two_player \
           --suffix _v2_all --raw-suffix _all --dqn-run dqn_two_player
Needs results/raw/ from simulate.py and saved models and evaluations from train.py and
evaluate.py. The first run listed is used for 4-player charts. ``--suffix`` picks which
evaluation files to chart, and ``--raw-suffix`` which tournament, such as ``_all`` for the
40-bot pool. ``--dqn-run`` adds that agent's 2-player row to the win-rate chart.
"""

import argparse
import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor
from functools import partial

import pandas as pd

from saltmarket.analysis import plots
from saltmarket.analysis import tournament_stats as stats
from saltmarket.analysis.tendencies import auction_prices, measure_tendencies
from saltmarket.bots.heldout.catalog import HELDOUT_BOTS
from saltmarket.bots.registry import make_any_bot
from saltmarket.paths import FIGURES, MODELS, RESULTS
from saltmarket.rl.agent import AgentStrategy
from saltmarket.rl.policy import NumpyPolicy, PolicyWeights

DEFAULT_BEHAVIOR_GAMES = 2600
CLOSE_VARIANT_SHARE = 0.4
"""A held-out bot playing at least this share of games exactly like a training bot."""
ANALYSIS_SEED = 5_000_000_000


def make_agent(weights: PolicyWeights) -> AgentStrategy:
    """Create a greedy agent from saved weights."""
    return AgentStrategy(NumpyPolicy(weights).greedy)


def _tendencies(task: tuple) -> pd.DataFrame:
    label, weights, bot, games = task
    maker = partial(make_agent, weights) if weights is not None else partial(make_any_bot, bot)
    return measure_tendencies(maker, label, games, ANALYSIS_SEED)


def _auction(task: tuple[str, int, int]) -> dict:
    return auction_prices(task[0], task[1], task[2], ANALYSIS_SEED + 1_000_000)


def behavior_tables(
    weights: PolicyWeights, best_bot: str, games: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Measure the agent's habits and auction prices, in parallel."""
    context = multiprocessing.get_context("spawn")
    workers = os.cpu_count() or 1
    with ProcessPoolExecutor(max_workers=workers, mp_context=context) as pool:
        players = [("PPO agent", weights, None, games), (best_bot, None, best_bot, games)]
        habits = pool.map(_tendencies, players)
        tasks = [(name, size, games) for name in (best_bot, "balanced") for size in (2, 4)]
        prices = pool.map(_auction, tasks)
        return pd.concat(list(habits), ignore_index=True), pd.DataFrame(list(prices))


def heldout_split(tables: dict[str, pd.DataFrame], overlap: pd.DataFrame) -> pd.DataFrame:
    """Pool each agent's results against close-variant and distinct held-out bots."""
    close = set(overlap.loc[overlap["identical_share"] >= CLOSE_VARIANT_SHARE, "heldout_bot"])
    rows = []
    for agent, table in tables.items():
        heldout = table[table["opponent"].isin(set(overlap["heldout_bot"]))]
        for group, part in heldout.groupby(heldout["opponent"].isin(close)):
            wins, games = int(part["wins"].sum()), int(part["games"].sum())
            low, high = stats.wilson_interval(wins, games)
            rows.append({"agent": agent, "group": "close_variant" if group else "distinct",
                         "bots": len(part), "games": games, "wins": wins,
                         "win_rate": wins / games, "ci_low": low, "ci_high": high})
    return pd.DataFrame(rows)


def main() -> None:
    """Build all tables and charts."""
    from saltmarket.rl.train import load_policy

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", nargs="+", default=["main"])
    parser.add_argument("--best-run", default="main", help="Run shown in 2-player charts.")
    parser.add_argument("--fresh", action="store_true", help="Same as --suffix _fresh.")
    parser.add_argument("--suffix", default="", help="Evaluation file suffix, like _v2_all.")
    parser.add_argument("--raw-suffix", default="", help="Tournament raw folder suffix.")
    parser.add_argument("--dqn-run", default="", help="DQN run to add to the win-rate chart.")
    parser.add_argument("--behavior-games", type=int, default=DEFAULT_BEHAVIOR_GAMES)
    args = parser.parse_args()
    FIGURES.mkdir(parents=True, exist_ok=True)

    two_rows = stats.load_rows(RESULTS / "raw" / f"round_robin{args.raw_suffix}")
    four_rows = stats.load_rows(RESULTS / "raw" / f"tables{args.raw_suffix}")
    levels = pd.concat(
        [stats.peak_level_win_rates(two_rows), stats.peak_level_win_rates(four_rows)],
        ignore_index=True,
    )
    levels.to_csv(RESULTS / "peak_level_win_rates.csv", index=False, float_format="%.5f")

    suffix = "_fresh" if args.fresh else args.suffix
    two_table = pd.read_csv(RESULTS / f"rl_vs_bots_two_player_{args.best_run}{suffix}.csv")
    if args.dqn_run:
        dqn = pd.read_csv(RESULTS / f"rl_vs_bots_two_player_{args.dqn_run}{suffix}.csv")
        two_table = pd.concat([two_table, dqn[dqn["bot"] == "dqn"]], ignore_index=True)
    heldout = frozenset(HELDOUT_BOTS)
    four_table = pd.read_csv(RESULTS / f"rl_vs_bots_four_player_{args.runs[0]}{suffix}.csv")
    best_bot = pd.read_csv(RESULTS / "two_player_win_rates.csv").iloc[0]["bot"]
    weights = load_policy(MODELS / f"{args.best_run}.npz")
    tendencies, prices = behavior_tables(weights, best_bot, args.behavior_games)
    tendencies.to_csv(RESULTS / "rl_tendencies.csv", index=False, float_format="%.5f")
    prices.to_csv(RESULTS / "auction_prices.csv", index=False, float_format="%.5f")

    landing = pd.read_csv(RESULTS / "landing_frequency.csv")
    plots.board_heatmap(landing, FIGURES / "board_heatmap.png")
    plots.ranked_win_rates(two_table, four_table, FIGURES / "win_rates.png", heldout)
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
        pd.read_csv(RESULTS / f"rl_eval_two_player_{args.best_run}{suffix}.csv"),
        FIGURES / "agent_vs_opponents.png",
        "PPO agent against each bot, 2 players",
        heldout,
    )
    plots.tendencies_chart(tendencies, FIGURES / "agent_tendencies.png")

    overlap_path = RESULTS / "heldout_overlap.csv"
    if overlap_path.exists():
        runs = {"ppo": args.best_run, **({"dqn": args.dqn_run} if args.dqn_run else {})}
        tables = {
            agent: pd.read_csv(RESULTS / f"rl_eval_two_player_{run}{suffix}.csv")
            for agent, run in runs.items()
        }
        heldout_split(tables, pd.read_csv(overlap_path)).to_csv(
            RESULTS / "heldout_split.csv", index=False, float_format="%.5f"
        )


if __name__ == "__main__":
    main()
