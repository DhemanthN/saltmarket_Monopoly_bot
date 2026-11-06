import os

import pytest
from conftest import give, make_state
from hypothesis import given, settings
from hypothesis import strategies as st

from saltmarket.bots.random_bot import RandomBot
from saltmarket.engine.config import GameConfig
from saltmarket.engine.game import Game
from saltmarket.engine.invariants import InvariantError, check_invariants
from saltmarket.sim.fuzz import fuzz_seeds, run_fuzz


def logged_game(seed, players=3):
    game = Game([RandomBot() for _ in range(players)], seed=seed, record_log=True)
    return game, game.play()


@pytest.mark.smoke
def test_same_seed_gives_identical_game():
    first, first_result = logged_game(42)
    second, second_result = logged_game(42)
    assert first.log == second.log
    assert first_result == second_result
    assert len(first.log) > 100


@pytest.mark.smoke
def test_different_seeds_give_different_games():
    assert logged_game(1)[0].log != logged_game(2)[0].log


@pytest.mark.smoke
def test_small_fuzz_batch():
    summary = fuzz_seeds(range(30))
    assert summary.games == 30


@settings(max_examples=40, deadline=None)
@given(
    seed=st.integers(0, 2**32 - 1),
    players=st.integers(2, 6),
    cash=st.integers(0, 3000),
    depots=st.integers(0, 40),
    ports=st.integers(0, 12),
    jackpot=st.booleans(),
)
def test_invariants_hold_for_any_config(seed, players, cash, depots, ports, jackpot):
    config = GameConfig(
        starting_cash=cash,
        total_depots=depots,
        total_ports=ports,
        calm_waters_jackpot=jackpot,
        turn_cap=300,
    )
    Game([RandomBot() for _ in range(players)], seed=seed, config=config, debug=True).play()


def tamper_money(state):
    state.players[0].cash += 1


def tamper_negative_cash(state):
    state.players[0].cash = -1
    state.burned += state.config.starting_cash + 1


def tamper_uneven(state):
    give(state, 0, 6, 8)
    state.level[6] = 2
    state.depots_left -= 2


def tamper_supply(state):
    give(state, 0, 6, 8)
    state.level[6] = state.level[8] = 1


def tamper_split_group(state):
    give(state, 0, 6)
    give(state, 1, 8)
    state.level[6] = state.level[8] = 1
    state.depots_left -= 2


def tamper_mortgaged_group(state):
    give(state, 0, 6, 8)
    state.level[6] = 1
    state.depots_left -= 1
    state.mortgaged[8] = True


def tamper_unowned_mortgage(state):
    state.mortgaged[6] = True


def tamper_bankrupt_owner(state):
    give(state, 0, 6)
    state.burned += state.players[0].cash
    state.players[0].cash = 0
    state.players[0].bankrupt = True


def tamper_lost_card(state):
    state.decks["tide"]._cards.pop()


@pytest.mark.smoke
@pytest.mark.parametrize(
    "tamper",
    [
        tamper_money,
        tamper_negative_cash,
        tamper_uneven,
        tamper_supply,
        tamper_split_group,
        tamper_mortgaged_group,
        tamper_unowned_mortgage,
        tamper_bankrupt_owner,
        tamper_lost_card,
    ],
)
def test_invariant_checker_catches_tampering(tamper):
    state = make_state()
    check_invariants(state)
    tamper(state)
    with pytest.raises(InvariantError):
        check_invariants(state)


@pytest.mark.slow
def test_fuzz_10000_games():
    summary = run_fuzz(10_000, workers=os.cpu_count() or 1)
    assert summary.games == 10_000
