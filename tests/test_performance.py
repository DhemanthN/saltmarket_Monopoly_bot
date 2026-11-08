"""Speed-ups must never change a game: exact regression checks and cache correctness."""

import json
from pathlib import Path

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from conftest import make_state
from saltmarket.bots.catalog import BOTS
from saltmarket.engine.dice import BATCH_ROLLS, RandomDice
from saltmarket.engine.state import MIXED
from saltmarket.sim.fingerprint import fingerprint_schedule, game_fingerprint

GOLDEN = Path(__file__).parent / "data" / "golden_games.json"
GOLDEN_GAMES = json.loads(GOLDEN.read_text(encoding="utf-8"))


@pytest.mark.smoke
@pytest.mark.parametrize("table_size", [2, 4])
def test_seeded_games_match_fingerprints_recorded_before_optimizing(table_size):
    """The golden file was written by the engine before any performance work."""
    expected = GOLDEN_GAMES[str(table_size)]
    schedule = fingerprint_schedule(sorted(BOTS), len(expected), table_size)
    assert [game_fingerprint(m) for m in schedule] == expected


def test_golden_games_seat_every_bot():
    seated = {name for games in GOLDEN_GAMES.values() for game in games for name in game["names"]}
    assert seated == set(BOTS)


@pytest.mark.smoke
@pytest.mark.parametrize("seed", [0, 1, 12345, 2**40])
def test_batched_dice_give_the_same_rolls_as_one_numpy_call_per_roll(seed):
    rolls = 3 * BATCH_ROLLS + 7
    dice = RandomDice(np.random.default_rng(seed))
    batched = [dice.roll() for _ in range(rolls)]
    rng = np.random.default_rng(seed)
    one_at_a_time = [tuple(int(face) for face in rng.integers(1, 7, size=2)) for _ in range(rolls)]
    assert batched == one_at_a_time


def _brute_force_views(state):
    owner = state.owner
    spaces = {p: [i for i in state.board.ownable if owner[i] == p] for p in (None, 0, 1, 2)}
    sole = {}
    for group, lots in state.board.groups.items():
        owners = {owner[i] for i in lots}
        sole[group] = owners.pop() if len(owners) == 1 else MIXED
    sites = {
        p: tuple(sorted(i for g, lots in state.board.groups.items() if sole[g] == p for i in lots))
        for p in (0, 1, 2)
    }
    return spaces, sole, sites


@pytest.mark.smoke
@settings(max_examples=60, deadline=None)
@given(st.lists(st.tuples(st.integers(0, 39), st.sampled_from([None, 0, 1, 2])), max_size=80))
def test_ownership_cache_matches_a_full_scan_after_any_sequence_of_writes(writes):
    state = make_state(num_players=3)
    ownable = state.board.ownable
    for step, (position, player) in enumerate(writes):
        state.owner[ownable[position % len(ownable)]] = player
        if step % 3:
            continue
        spaces, sole, sites = _brute_force_views(state)
        assert {p: state.spaces_of(p) for p in spaces} == spaces
        assert {g: state.group_owner(g) for g in sole} == sole
        assert {p: state.build_sites(p) for p in sites} == sites
        assert state.mixed_groups() == tuple(g for g in sole if sole[g] is MIXED)


def test_spaces_of_returns_a_copy_callers_can_change():
    state = make_state()
    state.owner[1] = 0
    state.spaces_of(0).append(99)
    assert state.spaces_of(0) == [1]
