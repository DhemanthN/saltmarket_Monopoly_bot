"""Run the bot tournaments and save summary tables to results/.

Usage: python scripts/simulate.py --games-per-pair 400 --tables 12500
Stopping and rerunning resumes where it left off, and larger numbers extend the run.
Raw per-game chunks go to results/raw/, and summaries go to results/.
"""

import argparse
import json
import os
import time
from pathlib import Path

import pandas as pd

from saltmarket.analysis import tournament_stats as stats
from saltmarket.bots.catalog import BOTS
from saltmarket.sim.tournament import (
    random_table_schedule,
    round_robin_schedule,
    run_tournament,
)

RESULTS = Path(__file__).resolve().parents[1] / "results"
RAW = RESULTS / "raw"
ROUND_ROBIN_SEED = 1_000_000_000
TABLE_SEED = 2_000_000_000
TABLE_SIZE = 4


def summarize(name: str, directory: Path) -> dict:
    """Write the per-tournament tables and return its headline numbers."""
    rows = stats.load_rows(directory)
    rates = stats.win_rates(rows)
    rates.to_csv(RESULTS / f"{name}_win_rates.csv", index=False, float_format="%.5f")
    stats.seat_win_rates(rows).to_csv(
        RESULTS / f"{name}_seats.csv", index=False, float_format="%.5f"
    )
    stats.group_value(rows).to_csv(
        RESULTS / f"{name}_group_value.csv", index=False, float_format="%.5f"
    )
    totals = stats.load_group_totals(directory)
    totals["rent_per_coin_spent"] = totals["rent_earned"] / totals["spent"]
    totals.to_csv(RESULTS / f"{name}_group_economics.csv", index=False, float_format="%.5f")
    half_widths = (rates["ci_high"] - rates["ci_low"]) / 2
    decided_widths = (rates["decided_ci_high"] - rates["decided_ci_low"]) / 2
    return {
        **stats.game_lengths(rows),
        "min_games_per_bot": int(rates["games"].min()),
        "max_ci_half_width": float(half_widths.max()),
        "max_decided_ci_half_width": float(decided_widths.max()),
    }


def summarize_pairs(directory: Path) -> None:
    """Write head-to-head matrices and ratings, over all games and decided games."""
    rows = stats.load_rows(directory)
    decided = rows[rows["hit_cap"] == 0]
    stats.head_to_head(rows).to_csv(RESULTS / "head_to_head.csv", float_format="%.4f")
    stats.head_to_head(decided).to_csv(RESULTS / "head_to_head_decided.csv", float_format="%.4f")
    ratings = pd.DataFrame(
        {
            "rating": stats.bradley_terry_ratings(rows),
            "decided_rating": stats.bradley_terry_ratings(decided),
        }
    ).sort_values("rating", ascending=False)
    ratings.to_csv(RESULTS / "ratings.csv", index_label="bot", float_format="%.1f")


def main() -> None:
    """Run both tournaments, then summarize them."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games-per-pair", type=int, default=400)
    parser.add_argument("--tables", type=int, default=12_500)
    parser.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    parser.add_argument("--name-suffix", default="", help="Keep a separate raw directory.")
    args = parser.parse_args()

    bots = sorted(BOTS)
    pairs_dir = RAW / f"round_robin{args.name_suffix}"
    tables_dir = RAW / f"tables{args.name_suffix}"
    started = time.perf_counter()
    run_tournament(
        round_robin_schedule(bots, args.games_per_pair, ROUND_ROBIN_SEED),
        pairs_dir,
        {"kind": "round_robin", "bots": bots, "base_seed": ROUND_ROBIN_SEED},
        args.workers,
    )
    run_tournament(
        random_table_schedule(bots, args.tables, TABLE_SIZE, TABLE_SEED),
        tables_dir,
        {"kind": "tables", "size": TABLE_SIZE, "bots": bots, "base_seed": TABLE_SEED},
        args.workers,
    )
    elapsed = time.perf_counter() - started

    summary = {
        "bots": len(bots),
        "games_per_pair": args.games_per_pair,
        "tables": args.tables,
        "this_run_seconds": elapsed,
        "two_player": summarize("two_player", pairs_dir),
        "four_player": summarize("four_player", tables_dir),
    }
    summarize_pairs(pairs_dir)
    (RESULTS / "tournament_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
