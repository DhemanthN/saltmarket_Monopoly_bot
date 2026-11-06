from collections import Counter

import numpy as np
import pandas as pd
import pytest

from conftest import give
from saltmarket.analysis import tournament_stats as stats
from saltmarket.bots.base import Strategy
from saltmarket.engine import bank
from saltmarket.engine.game import Game
from saltmarket.sim.tournament import (
    Matchup,
    play_matchup,
    random_table_schedule,
    round_robin_schedule,
    run_chunk,
    run_tournament,
)

pytestmark = pytest.mark.smoke
BOTS = ["always_buy", "expert", "never_buy", "random"]


def rows_for(results):
    """Build 2-player rows from (first, second, first_won, hit_cap) tuples."""
    rows = []
    for game_id, (first, second, first_won, hit_cap) in enumerate(results):
        for seat, (bot, won) in enumerate(((first, first_won), (second, 1 - first_won))):
            rows.append(
                {"game_id": game_id, "seat": seat, "bot": bot, "won": won, "turns": 100,
                 "hit_cap": hit_cap, "bankrupt_cause": "", "groups_completed": ""}
            )
    return pd.DataFrame(rows)


# Schedules


def test_round_robin_plays_every_pair_equally_with_both_seat_orders():
    schedule = round_robin_schedule(BOTS, 4, 100)
    assert len(schedule) == 6 * 4
    assert set(Counter(frozenset(m.names) for m in schedule).values()) == {4}
    assert set(Counter(m.names for m in schedule).values()) == {2}


def test_every_game_has_a_unique_id_and_seed():
    schedule = round_robin_schedule(BOTS, 4, 100)
    assert len({m.game_id for m in schedule}) == len(schedule)
    assert len({m.seed for m in schedule}) == len(schedule)


def test_random_tables_rotate_each_bot_through_every_seat():
    schedule = random_table_schedule(BOTS, 3, 4, 200)
    assert len(schedule) == 12
    table = schedule[:4]
    assert all(len(set(m.names)) == 4 for m in table)
    assert all(len({m.names[seat] for m in table}) == 4 for seat in range(4))


@pytest.mark.parametrize(
    "make",
    [
        lambda n: round_robin_schedule(BOTS, n, 1),
        lambda n: random_table_schedule(BOTS, n, 3, 1),
    ],
)
def test_extending_a_schedule_only_appends(make):
    short, long = make(4), make(6)
    assert long[: len(short)] == short


# Engine tracking


def test_rent_and_spending_are_tracked():
    class Buyer(Strategy):
        def should_buy(self, state, index):
            return True

    game = Game([Buyer(), Strategy()], seed=1)
    state = game.state
    game._offer_for_sale(state.players[0], 6)
    assert state.spent[6] == 90
    state.players[1].position = 6
    game._resolve_ownable(state.players[1], 6, lambda: 25)
    assert state.rent_earned[6] == 25


def test_build_tracks_spend_and_peak_level():
    game = Game([Strategy(), Strategy()], seed=1)
    state = game.state
    give(state, 0, 6, 8)
    bank.build(state, 0, 6)
    assert state.spent[6] == state.board[6].build_cost
    assert state.peak_level == [1, 0]


def test_first_completed_keeps_the_first_seat():
    game = Game([Strategy(), Strategy()], seed=1)
    state = game.state
    give(state, 1, 6, 8)
    game._track_completed_groups()
    give(state, 0, 6, 8)
    game._track_completed_groups()
    assert state.first_completed == {"reef": 1}


def test_bankruptcy_cause_is_tracked():
    game = Game([Strategy(), Strategy(), Strategy()], seed=1)
    players = game.state.players
    players[0].cash = 0
    game.charge(players[0], 10, players[1])
    players[2].cash = 0
    game.charge(players[2], 10, None)
    assert game.state.bankruptcies == [(0, 1), (2, None)]


# Playing and resuming


def test_play_matchup_row_contents():
    rows, groups = play_matchup(Matchup(7, ("expert", "always_buy"), 123))
    assert [row["bot"] for row in rows] == ["expert", "always_buy"]
    assert sum(row["won"] for row in rows) == 1
    assert {row["game_id"] for row in rows} == {7}
    assert len(groups) == 8


def test_same_matchup_gives_same_rows():
    matchup = Matchup(1, ("expert", "random", "port_rush", "balanced"), 9)
    assert play_matchup(matchup) == play_matchup(matchup)


def small_run(directory, schedule, workers=1, chunk_size=2):
    return run_tournament(schedule, directory, {"kind": "test"}, workers, chunk_size)


def test_tournament_resumes_without_replaying(tmp_path):
    schedule = round_robin_schedule(["never_buy", "random"], 4, 5)
    run_chunk(tmp_path, 0, schedule[:2])
    assert small_run(tmp_path, schedule) == 2
    assert small_run(tmp_path, schedule) == 0
    assert len(stats.load_rows(tmp_path)) == 8


def test_partial_chunk_is_replayed_when_schedule_grows(tmp_path):
    bots = ["never_buy", "random"]
    assert small_run(tmp_path, round_robin_schedule(bots, 3, 5)) == 3
    assert small_run(tmp_path, round_robin_schedule(bots, 4, 5)) == 2
    assert stats.load_rows(tmp_path)["game_id"].nunique() == 4


def test_resumed_results_match_an_uninterrupted_run(tmp_path):
    schedule = round_robin_schedule(["never_buy", "random"], 4, 5)
    interrupted, clean = tmp_path / "a", tmp_path / "b"
    interrupted.mkdir()
    run_chunk(interrupted, 1, schedule[2:])
    small_run(interrupted, schedule)
    small_run(clean, schedule)
    pd.testing.assert_frame_equal(stats.load_rows(interrupted), stats.load_rows(clean))


def test_different_tournament_in_same_directory_is_refused(tmp_path):
    schedule = round_robin_schedule(["never_buy", "random"], 2, 5)
    run_tournament(schedule, tmp_path, {"kind": "one"}, 1)
    with pytest.raises(ValueError):
        run_tournament(schedule, tmp_path, {"kind": "two"}, 1)


# Statistics


@pytest.mark.parametrize(
    ("wins", "games", "low", "high"),
    [
        (5, 10, 0.2366, 0.7634),
        (0, 10, 0.0, 0.2775),
        (10, 10, 0.7225, 1.0),
        (81, 263, 0.2553, 0.3662),
    ],
)
def test_wilson_known_values(wins, games, low, high):
    assert stats.wilson_interval(wins, games) == pytest.approx((low, high), abs=2e-4)


def test_wilson_with_no_games_is_uninformative():
    assert stats.wilson_interval(0, 0) == (0.0, 1.0)


def test_win_rates_report_all_and_decided_games():
    rows = rows_for([("a", "b", 1, 1), ("a", "b", 1, 1), ("a", "b", 0, 0), ("a", "b", 0, 0)])
    table = stats.win_rates(rows).set_index("bot")
    assert table.loc["a", "win_rate"] == 0.5
    assert table.loc["a", "decided_win_rate"] == 0.0
    assert table.loc["b", "decided_win_rate"] == 1.0
    assert table.loc["a", "cap_rate"] == 0.5


def test_head_to_head_is_symmetric():
    rows = rows_for([("a", "b", 1, 0), ("b", "a", 0, 0), ("a", "b", 0, 0), ("a", "c", 1, 0)])
    matrix = stats.head_to_head(rows)
    assert matrix.loc["a", "b"] == pytest.approx(2 / 3)
    assert matrix.loc["b", "a"] == pytest.approx(1 / 3)
    assert matrix.loc["a", "c"] == 1.0


def test_ratings_recover_known_strengths():
    rng = np.random.default_rng(0)
    truth = {"a": 1700.0, "b": 1500.0, "c": 1300.0}
    results = []
    for first, second in (("a", "b"), ("a", "c"), ("b", "c")):
        chance = 1 / (1 + 10 ** ((truth[second] - truth[first]) / 400))
        results += [(first, second, int(rng.random() < chance), 0) for _ in range(4000)]
    ratings = stats.bradley_terry_ratings(rows_for(results))
    assert ratings["a"] - ratings["b"] == pytest.approx(200, abs=25)
    assert ratings["b"] - ratings["c"] == pytest.approx(200, abs=25)
    assert ratings.mean() == pytest.approx(1500, abs=1)


def test_ratings_do_not_depend_on_game_order():
    results = [("a", "b", 1, 0), ("a", "b", 1, 0), ("b", "c", 1, 0), ("a", "c", 0, 0)]
    first = stats.bradley_terry_ratings(rows_for(results))
    second = stats.bradley_terry_ratings(rows_for(results[::-1]))
    pd.testing.assert_series_equal(first, second)


def test_game_lengths_count_each_game_once():
    rows = rows_for([("a", "b", 1, 0), ("a", "b", 1, 1)])
    lengths = stats.game_lengths(rows)
    assert lengths["games"] == 2 and lengths["cap_rate"] == 0.5


def test_group_value_compares_holders_with_others():
    rows = rows_for([("a", "b", 1, 0), ("a", "b", 1, 0), ("a", "b", 0, 0), ("a", "b", 0, 0)])
    rows.loc[rows["bot"] == "a", "groups_completed"] = ["amber|jade", "amber", "", ""]
    table = stats.group_value(rows).set_index("group")
    assert table.loc["amber", "holder_win_rate"] == 1.0
    assert table.loc["amber", "other_win_rate"] == pytest.approx(2 / 6)
    assert table.loc["jade", "holder_games"] == 1


def test_seat_win_rates_sum_to_one_in_two_player_games():
    rows = rows_for([("a", "b", 1, 0), ("a", "b", 0, 0), ("a", "b", 1, 0)])
    assert stats.seat_win_rates(rows)["win_rate"].sum() == pytest.approx(1.0)
