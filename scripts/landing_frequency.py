"""Compare simulated landing frequencies with the exact Markov chain answer.

Usage: python scripts/landing_frequency.py --games 400 --turns 4000
Writes results/landing_frequency.csv, results/landing_summary.json, and
results/figures/landing_frequency.png.
"""

import argparse
import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from saltmarket.analysis.style import INK_SECONDARY, SERIES, SURFACE, apply_style
from saltmarket.engine.board import default_board
from saltmarket.engine.cards import default_cards
from saltmarket.engine.config import GameConfig
from saltmarket.engine.markov import landing_probabilities
from saltmarket.paths import RESULTS
from saltmarket.sim.landing import simulate_landings

LABELLED_SPACES = 3


def build_table(counts: np.ndarray) -> pd.DataFrame:
    """Return one row per space with simulated and exact landing rates."""
    board = default_board()
    exact = landing_probabilities(board, default_cards(), GameConfig())
    return pd.DataFrame(
        {
            "index": range(board.size),
            "name": [s.name for s in board.spaces],
            "kind": [s.kind.value for s in board.spaces],
            "visits": counts,
            "simulated": counts / counts.sum(),
            "exact": exact,
        }
    )


def plot(table: pd.DataFrame, path: Path) -> None:
    """Draw simulated bars with exact markers in board order."""
    apply_style()
    fig, ax = plt.subplots(figsize=(12, 5.6), layout="constrained")
    ax.bar(table["index"], table["simulated"] * 100, width=0.72, color=SERIES[0],
           label="Simulated (game engine)")
    ax.scatter(table["index"], table["exact"] * 100, s=34, color=SERIES[1],
               edgecolor=SURFACE, linewidth=1.2, zorder=3, label="Exact (Markov chain)")
    for row in table.nlargest(LABELLED_SPACES, "simulated").itertuples():
        ax.annotate(f"{row.simulated:.1%}", (row.index, row.simulated * 100),
                    xytext=(0, 7), textcoords="offset points", ha="center",
                    fontsize=9, color=INK_SECONDARY)
    ax.set_xticks(table["index"], table["name"], rotation=60, ha="right",
                  rotation_mode="anchor", fontsize=8.5)
    ax.set_xlim(-0.8, len(table) - 0.2)
    ax.set_ylim(0, table["simulated"].max() * 118)
    ax.yaxis.set_major_formatter(lambda value, _: f"{value:.0f}%")
    ax.set_ylabel("Share of rolls ending on this space")
    ax.set_title("Where players end up on the Saltmarket board")
    ax.legend(loc="upper right", ncols=2)
    fig.savefig(path)
    plt.close(fig)


def main() -> None:
    """Run the simulation and save the table, summary, and chart."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=int, default=400)
    parser.add_argument("--turns", type=int, default=4000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    counts = simulate_landings(args.games, args.turns, os.cpu_count() or 1, args.seed)
    table = build_table(counts)
    (RESULTS / "figures").mkdir(parents=True, exist_ok=True)
    table.to_csv(RESULTS / "landing_frequency.csv", index=False, float_format="%.6f")
    plot(table, RESULTS / "figures" / "landing_frequency.png")

    gap = (table["simulated"] - table["exact"]).abs()
    top = table.nlargest(5, "simulated")
    summary = {
        "games": args.games,
        "turns_per_game": args.turns,
        "seed": args.seed,
        "rolls": int(counts.sum()),
        "total_variation_distance": float(gap.sum() / 2),
        "largest_gap": float(gap.max()),
        "top_spaces": top[["name", "simulated", "exact"]].to_dict("records"),
    }
    (RESULTS / "landing_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
