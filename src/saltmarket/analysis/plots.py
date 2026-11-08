"""Chart functions. Each one takes tables and saves a single PNG."""

import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

from saltmarket.analysis.style import AXIS, INK, INK_SECONDARY, SERIES, SURFACE, apply_style

BLUE_RAMP = ("#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b")
DIVERGING = ("#e34948", "#f0efec", "#2a78d6")
AGENT_COLOR = SERIES[1]
BOT_COLOR = SERIES[0]
BOARD_SIDE = 11


def _save(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path)
    plt.close(fig)


def _percent_axis(axis) -> None:
    axis.set_major_formatter(lambda value, _: f"{value:.0f}%")


def _error_bars(table: pd.DataFrame) -> list[np.ndarray]:
    """Return lower and upper bar lengths, clipped because rounding can make them negative."""
    rate = table["win_rate"].to_numpy() * 100
    lower = rate - table["ci_low"].to_numpy() * 100
    upper = table["ci_high"].to_numpy() * 100 - rate
    return [np.clip(lower, 0, None), np.clip(upper, 0, None)]


def board_position(index: int) -> tuple[int, int]:
    """Return the (row, column) of a space on an 11 by 11 ring, starting bottom right."""
    last = BOARD_SIDE - 1
    if index <= last:
        return last, last - index
    if index <= 2 * last:
        return 2 * last - index, 0
    if index <= 3 * last:
        return 0, index - 2 * last
    return index - 3 * last, last


def board_heatmap(table: pd.DataFrame, path: Path) -> None:
    """Draw landing rates in the shape of the board."""
    apply_style()
    fig, ax = plt.subplots(figsize=(9.5, 9.5), layout="constrained")
    ax.grid(False)
    cmap = LinearSegmentedColormap.from_list("blue", BLUE_RAMP)
    others = table[table["name"] != "The Brig"]
    low, high = others["exact"].min() * 100, others["exact"].max() * 100
    for row in table.itertuples():
        y, x = board_position(row.index)
        value = max(0.0, row.exact * 100)
        level = min(1.0, max(0.0, (value - low) / (high - low)))
        ax.add_patch(
            plt.Rectangle((x, BOARD_SIDE - 1 - y), 0.96, 0.96, color=cmap(level), lw=0)
        )
        ink = "#ffffff" if level > 0.55 else INK
        label = textwrap.fill(row.name, 12, break_long_words=False)
        center_x, center_y = x + 0.48, BOARD_SIDE - 1 - y + 0.48
        ax.text(center_x, center_y + 0.14, label, ha="center", va="center", fontsize=6.3,
                color=ink, linespacing=0.95)
        ax.text(center_x, center_y - 0.27, f"{value:.1f}%", ha="center", va="center",
                fontsize=8, color=ink, fontweight="semibold")
    ax.text(BOARD_SIDE / 2, BOARD_SIDE / 2 + 0.3, "Saltmarket", ha="center", fontsize=24,
            fontweight="semibold")
    ax.text(BOARD_SIDE / 2, BOARD_SIDE / 2 - 0.4,
            "Share of rolls ending on each space\nThe Brig is off the color scale at "
            f"{table['exact'].max():.1%}", ha="center", va="top", fontsize=10.5,
            color=INK_SECONDARY)
    ax.set_xlim(-0.1, BOARD_SIDE)
    ax.set_ylim(-0.1, BOARD_SIDE)
    ax.set_aspect("equal")
    ax.axis("off")
    _save(fig, path)


def _ranked_panel(ax, table: pd.DataFrame, title: str, baseline: float) -> None:
    table = table.sort_values("win_rate")
    y = np.arange(len(table))
    rate = table["win_rate"] * 100
    colors = [AGENT_COLOR if bot == "ppo" else BOT_COLOR for bot in table["bot"]]
    errors = _error_bars(table)
    ax.barh(y, rate, height=0.68, color=colors)
    ax.errorbar(rate, y, xerr=errors, fmt="none", ecolor=INK, elinewidth=1, capsize=2)
    ax.axvline(baseline, color=INK_SECONDARY, lw=1)
    ax.text(baseline, len(table) - 0.2, f" even chance {baseline:.0f}%", fontsize=8.5,
            color=INK_SECONDARY, va="bottom")
    ax.set_yticks(y, table["bot"], fontsize=9)
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    _percent_axis(ax.xaxis)
    ax.set_title(title, pad=16)


def ranked_win_rates(two: pd.DataFrame, four: pd.DataFrame, path: Path) -> None:
    """Draw every player's win rate with 95% intervals at both table sizes."""
    apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(13, 8.2), layout="constrained")
    _ranked_panel(axes[0], two, "2 players", 50)
    _ranked_panel(axes[1], four, "4 players", 25)
    axes[0].set_xlabel("Win rate with 95% interval")
    axes[1].set_xlabel("Win rate with 95% interval")
    _save(fig, path)


def head_to_head_heatmap(matrix: pd.DataFrame, path: Path) -> None:
    """Draw the 2-player head-to-head matrix, strongest bots first."""
    apply_style()
    order = matrix.mean(axis=1).sort_values(ascending=False).index
    ordered = matrix.loc[order, order] * 100
    fig, ax = plt.subplots(figsize=(11.5, 10), layout="constrained")
    ax.grid(False)
    cmap = LinearSegmentedColormap.from_list("div", DIVERGING)
    image = ax.imshow(ordered, cmap=cmap, norm=TwoSlopeNorm(50, 0, 100))
    ax.set_xticks(range(len(order)), order, rotation=60, ha="right", rotation_mode="anchor",
                  fontsize=8.5)
    ax.set_yticks(range(len(order)), order, fontsize=8.5)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    bar = fig.colorbar(image, ax=ax, shrink=0.7)
    bar.set_label("Row bot's win rate against column bot")
    _percent_axis(bar.ax.yaxis)
    bar.outline.set_visible(False)
    ax.set_title("Head-to-head results, 400 games per pair")
    _save(fig, path)


def ratings_leaderboard(ratings: pd.DataFrame, path: Path) -> None:
    """Draw 2-player ratings as a ranked dot plot."""
    apply_style()
    table = ratings.sort_values("rating")
    fig, ax = plt.subplots(figsize=(8.5, 8), layout="constrained")
    y = np.arange(len(table))
    ax.hlines(y, table["rating"].min() - 40, table["rating"], color=AXIS, lw=1)
    ax.scatter(table["rating"], y, s=46, color=BOT_COLOR, zorder=3)
    ax.axvline(1500, color=INK_SECONDARY, lw=1)
    ax.set_yticks(y, table["bot"], fontsize=9)
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Elo-scale rating (Bradley-Terry fit, average bot = 1500)")
    ax.set_title("Strategy ratings from 2-player games")
    best = table.iloc[-1]
    ax.annotate(f"{best['rating']:.0f}", (best["rating"], len(table) - 1), xytext=(8, -3),
                textcoords="offset points", fontsize=9, color=INK_SECONDARY)
    _save(fig, path)


def game_length_distribution(two: pd.DataFrame, four: pd.DataFrame, path: Path) -> None:
    """Draw how long games last at each table size, marking the turn cap."""
    apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), layout="constrained", sharex=True)
    bins = np.arange(0, 2050, 50)
    for ax, rows, title in ((axes[0], two, "2 players"), (axes[1], four, "4 players")):
        games = rows.drop_duplicates("game_id")
        weights = np.full(len(games), 100 / len(games))
        ax.hist(games["turns"], bins=bins, weights=weights, color=BOT_COLOR, rwidth=0.86)
        capped = games["hit_cap"].mean()
        ax.text(0.86, 0.5, f"{capped:.1%} of games\nhit the turn cap", ha="right",
                transform=ax.transAxes, fontsize=9.5, color=INK_SECONDARY)
        ax.set_title(title)
        ax.set_xlabel("Player turns in the game")
        _percent_axis(ax.yaxis)
    axes[0].set_ylabel("Share of games")
    _save(fig, path)


def group_roi(two: pd.DataFrame, four: pd.DataFrame, path: Path) -> None:
    """Draw rent earned per coin spent by group, in board order."""
    apply_style()
    order = ["kelp", "reef", "coral", "driftwood", "amber", "cinder", "jade", "crown"]
    left = two.set_index("group").loc[order, "rent_per_coin_spent"]
    right = four.set_index("group").loc[order, "rent_per_coin_spent"]
    fig, ax = plt.subplots(figsize=(10, 4.8), layout="constrained")
    x = np.arange(len(order))
    ax.bar(x - 0.2, left, width=0.36, color=SERIES[0], label="2 players")
    ax.bar(x + 0.2, right, width=0.36, color=SERIES[1], label="4 players")
    ax.set_xticks(x, order)
    ax.set_ylabel("Rent earned per coin spent")
    ax.set_title("Return on investment by island group, in board order")
    ax.legend(loc="upper right", ncols=2)
    _save(fig, path)


def building_level_effect(table: pd.DataFrame, path: Path) -> None:
    """Draw win rate by the highest building level a player reached."""
    apply_style()
    fig, ax = plt.subplots(figsize=(9, 4.8), layout="constrained")
    labels = ["None", "1 depot", "2 depots", "3 depots", "4 depots", "Port"]
    for color, (size, part) in zip(SERIES, table.groupby("table_size"), strict=False):
        rate = part["win_rate"] * 100
        errors = _error_bars(part)
        ax.errorbar(part["peak_level"], rate, yerr=errors, color=color, lw=2, marker="o",
                    markersize=7, capsize=3, label=f"{size} players")
    ax.set_xticks(range(6), labels)
    ax.set_ylim(0, 100)
    _percent_axis(ax.yaxis)
    ax.set_xlabel("Highest building level the player ever reached")
    ax.set_ylabel("Win rate with 95% interval")
    ax.set_title("Players who build higher win more often")
    ax.legend(loc="upper left")
    _save(fig, path)


def training_curves(logs: dict[str, pd.DataFrame], path: Path) -> None:
    """Draw smoothed reward and win rate against training steps, one panel per measure."""
    apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), layout="constrained", sharex=True)
    window = 15
    for color, (label, log) in zip(SERIES, logs.items(), strict=False):
        steps = log["steps"] / 1e6
        axes[0].plot(steps, log["mean_return"].rolling(window, min_periods=1).mean(),
                     color=color, lw=2, label=label)
        axes[1].plot(steps, log["win_rate"].rolling(window, min_periods=1).mean() * 100,
                     color=color, lw=2, label=label)
    first = next(iter(logs.values()))
    for ax in axes:
        stages = first.groupby("stage", sort=False)
        for position, (stage, part) in enumerate(stages):
            start = part["steps"].min() / 1e6
            ax.axvline(start, color=AXIS, lw=1)
            ax.text(start, 1.0 + 0.045 * (position % 2), f" {stage}", fontsize=8,
                    transform=ax.get_xaxis_transform(), color=INK_SECONDARY, va="bottom")
        ax.set_xlabel("Training steps (millions)")
    axes[0].set_ylabel("Mean episode reward")
    axes[1].set_ylabel("Win rate while training")
    _percent_axis(axes[1].yaxis)
    axes[0].legend(loc="lower right")
    fig.suptitle("Opponents get harder at each stage, so a falling curve is not forgetting",
                 x=0.01, ha="left", fontsize=13, fontweight="semibold", y=1.09)
    _save(fig, path)


def agent_vs_opponents(table: pd.DataFrame, path: Path, title: str) -> None:
    """Draw the agent's win rate against each bot with 95% intervals."""
    apply_style()
    table = table.sort_values("win_rate")
    fig, ax = plt.subplots(figsize=(8.5, 8), layout="constrained")
    y = np.arange(len(table))
    rate = table["win_rate"] * 100
    errors = _error_bars(table)
    ax.barh(y, rate, height=0.68, color=AGENT_COLOR)
    ax.errorbar(rate, y, xerr=errors, fmt="none", ecolor=INK, elinewidth=1, capsize=2)
    ax.axvline(50, color=INK_SECONDARY, lw=1)
    ax.set_yticks(y, table["opponent"], fontsize=9)
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, 104)
    _percent_axis(ax.xaxis)
    ax.set_xlabel("Agent win rate with 95% interval")
    ax.set_title(title)
    _save(fig, path)


def tendencies_chart(table: pd.DataFrame, path: Path) -> None:
    """Compare the agent's habits with the best bot's, by board category."""
    apply_style()
    order = ["kelp", "reef", "coral", "driftwood", "amber", "cinder", "jade", "crown",
             "ferry", "utility"]
    players = list(table["player"].unique())
    measures = (
        ("buy_rate", "Buys at list price when offered", 100, True),
        ("mean_bid_share", "Mean auction bid, share of list price", 100, True),
        ("builds_per_game", "Building levels added per game", 1, False),
        ("trade_offers_per_game", "Trade offers per game", 1, False),
    )
    fig, axes = plt.subplots(2, 2, figsize=(13, 7.6), layout="constrained")
    x = np.arange(len(order))
    for ax, (column, title, scale, percent) in zip(axes.flat, measures, strict=True):
        colors = (AGENT_COLOR, BOT_COLOR)
        for slot, (player, color) in enumerate(zip(players, colors, strict=False)):
            part = table[table["player"] == player].set_index("category").reindex(order)
            ax.bar(x + (slot - 0.5) * 0.38, part[column].fillna(0) * scale, width=0.35,
                   color=color, label=player)
        ax.set_xticks(x, order, rotation=30, ha="right", fontsize=9)
        ax.set_title(title, fontsize=11.5)
        if percent:
            _percent_axis(ax.yaxis)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside upper right", ncols=2)
    _save(fig, path)


def agent_comparison(
    curves: dict[str, pd.DataFrame], tables: dict[str, pd.DataFrame], path: Path
) -> None:
    """Compare two agents: training win rate against steps, and held-out win rates.

    ``curves`` are pooled learning curves from ``compare.learning_curve``, and ``tables``
    are per-opponent evaluation tables. The first agent sets the opponent order.
    """
    apply_style()
    fig, axes = plt.subplots(
        1, 2, figsize=(13, 8.2), layout="constrained", width_ratios=(1.15, 1)
    )
    colors = dict(zip(curves, (SERIES[1], SERIES[2]), strict=False))
    curve_ax, opponent_ax = axes
    first = next(iter(curves.values()))
    for position, (stage, part) in enumerate(first.groupby("stage", sort=False)):
        start = (part["steps"].min() - (first["steps"].iloc[0])) / 1e6
        curve_ax.axvline(start, color=AXIS, lw=1)
        curve_ax.text(start, 0.99 - 0.035 * (position % 2), f" {stage}", fontsize=8,
                      transform=curve_ax.get_xaxis_transform(), color=INK_SECONDARY,
                      va="top")
    for label, curve in curves.items():
        curve_ax.plot(curve["steps"] / 1e6, curve["win_rate"] * 100, color=colors[label],
                      lw=2, label=label)
    curve_ax.set_xlabel("Training decisions (millions)")
    curve_ax.set_ylabel("Win rate while training, pooled per 500,000 decisions")
    curve_ax.set_ylim(0, 100)
    _percent_axis(curve_ax.yaxis)
    curve_ax.legend(loc="lower right")
    curve_ax.set_title("Learning curves on the same curriculum", pad=12)

    order = next(iter(tables.values())).sort_values("win_rate")["opponent"].tolist()
    y = np.arange(len(order))
    offsets = dict(zip(tables, (0.17, -0.17), strict=False))
    for label, table in tables.items():
        table = table.set_index("opponent").loc[order].reset_index()
        rate = table["win_rate"] * 100
        opponent_ax.errorbar(
            rate, y + offsets[label], xerr=_error_bars(table), fmt="o", ms=5,
            color=colors[label], ecolor=colors[label], elinewidth=1, capsize=0,
            mec=SURFACE, mew=1, label=label,
        )
    opponent_ax.axvline(50, color=INK_SECONDARY, lw=1)
    opponent_ax.text(50, len(order) - 0.3, " even chance 50%", fontsize=8.5,
                     color=INK_SECONDARY, va="bottom")
    opponent_ax.set_yticks(y, order, fontsize=9)
    opponent_ax.grid(axis="x")
    opponent_ax.grid(axis="y", visible=False)
    opponent_ax.set_xlim(0, 104)
    _percent_axis(opponent_ax.xaxis)
    opponent_ax.set_xlabel("Win rate on fresh held-out seeds, with 95% interval")
    opponent_ax.legend(loc="lower left")
    opponent_ax.set_title("Against each bot, 400 games each", pad=12)
    _save(fig, path)
