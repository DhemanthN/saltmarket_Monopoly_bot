from collections import Counter

import matplotlib
import numpy as np
import pandas as pd
import pytest

from saltmarket.analysis import plots
from saltmarket.analysis import tournament_stats as stats
from saltmarket.analysis.tendencies import (
    TendencyProbe,
    auction_prices,
    measure_tendencies,
    space_category,
)
from saltmarket.bots.base import Strategy
from saltmarket.bots.catalog import make_bot
from saltmarket.engine.game import Game

matplotlib.use("Agg")
pytestmark = pytest.mark.smoke
GROUPS = ["kelp", "reef", "coral", "driftwood", "amber", "cinder", "jade", "crown"]


def test_board_positions_form_a_ring_of_unique_edge_cells():
    cells = [plots.board_position(i) for i in range(40)]
    assert len(set(cells)) == 40
    assert all(0 in cell or 10 in cell for cell in cells)
    assert cells[0] == (10, 10) and cells[10] == (10, 0)
    assert cells[20] == (0, 0) and cells[30] == (0, 10)


def test_neighbouring_spaces_touch_on_the_ring():
    cells = [plots.board_position(i) for i in range(40)]
    for first, second in zip(cells, cells[1:] + cells[:1], strict=True):
        assert abs(first[0] - second[0]) + abs(first[1] - second[1]) == 1


def test_space_category(state):
    assert space_category(state, 6) == "reef"
    assert space_category(state, 5) == "ferry"
    assert space_category(state, 12) == "utility"


def test_probe_does_not_change_the_game():
    def play(wrap):
        counts = Counter()
        first = make_bot("expert")
        bots = [TendencyProbe(first, counts) if wrap else first, make_bot("always_buy")]
        game = Game(bots, seed=11, record_log=True)
        game.play()
        return game.log, counts

    plain, _ = play(False)
    watched, counts = play(True)
    assert plain == watched
    assert sum(value for (_, kind), value in counts.items() if kind == "buy_offers") > 0


def test_measure_tendencies_rates_are_valid():
    table = measure_tendencies(lambda: make_bot("always_buy"), "x", 6, 100)
    assert set(table["player"]) == {"x"}
    assert table["buy_rate"].dropna().between(0, 1).all()


def test_never_buy_has_no_buys():
    table = measure_tendencies(Strategy, "passive", 3, 1)
    assert (table["buy_rate"].dropna() == 0).all()


def test_auction_prices_report_share_of_list():
    result = auction_prices("auction_sniper", 2, 8, 50)
    assert result["auction_wins_per_game"] > 0
    assert 0 < result["share_of_list_price_paid"] <= 2


def test_peak_level_win_rates():
    rows = pd.DataFrame(
        {"table_size": 2, "peak_level": [0, 0, 3, 3], "won": [0, 0, 1, 0]}
    )
    table = stats.peak_level_win_rates(rows).set_index("peak_level")
    assert table.loc[0, "win_rate"] == 0.0
    assert table.loc[3, "win_rate"] == 0.5
    assert table.loc[3, "games"] == 2


def rate_table(names):
    return pd.DataFrame(
        {"bot": names, "win_rate": 0.5, "ci_low": 0.4, "ci_high": 0.6, "opponent": names}
    )


def assert_png(path):
    assert path.exists() and path.stat().st_size > 5000


def test_error_bars_survive_rounding_at_a_zero_win_rate(tmp_path):
    low = 1e-17
    levels = pd.DataFrame(
        {"table_size": 2, "peak_level": [0, 1], "win_rate": [0.0, 0.5],
         "ci_low": [low, 0.4], "ci_high": [0.1, 0.6]}
    )
    path = tmp_path / "levels.png"
    plots.building_level_effect(levels, path)
    assert_png(path)


def test_chart_functions_write_images(tmp_path):
    names = ["ppo", "a", "b"]
    landing = pd.DataFrame(
        {
            "index": range(40),
            "name": [f"Space {i}" for i in range(39)] + ["The Brig"],
            "exact": np.linspace(0.01, 0.12, 40),
        }
    )
    matrix = pd.DataFrame(0.5, index=names, columns=names)
    rows = pd.DataFrame({"game_id": range(50), "turns": range(50), "hit_cap": 0})
    economics = pd.DataFrame({"group": GROUPS, "rent_per_coin_spent": 1.0})
    levels = pd.DataFrame(
        {"table_size": 2, "peak_level": range(6), "win_rate": 0.5, "ci_low": 0.4, "ci_high": 0.6}
    )
    log = pd.DataFrame(
        {"steps": [1, 2, 3], "stage": ["x", "x", "y"], "mean_return": 0.1, "win_rate": 0.5}
    )
    habits = pd.DataFrame(
        {
            "player": ["p", "q"],
            "category": ["kelp", "kelp"],
            "buy_rate": 0.5,
            "mean_bid_share": 0.5,
            "builds_per_game": 1.0,
            "trade_offers_per_game": 1.0,
        }
    )
    calls = {
        "board": lambda p: plots.board_heatmap(landing, p),
        "rates": lambda p: plots.ranked_win_rates(rate_table(names), rate_table(names), p),
        "h2h": lambda p: plots.head_to_head_heatmap(matrix, p),
        "ratings": lambda p: plots.ratings_leaderboard(
            pd.DataFrame({"bot": names, "rating": [1600.0, 1500.0, 1400.0]}), p
        ),
        "length": lambda p: plots.game_length_distribution(rows, rows, p),
        "roi": lambda p: plots.group_roi(economics, economics, p),
        "levels": lambda p: plots.building_level_effect(levels, p),
        "curves": lambda p: plots.training_curves({"run": log}, p),
        "agent": lambda p: plots.agent_vs_opponents(rate_table(names), p, "Title"),
        "habits": lambda p: plots.tendencies_chart(habits, p),
    }
    for name, draw in calls.items():
        path = tmp_path / f"{name}.png"
        draw(path)
        assert_png(path)
