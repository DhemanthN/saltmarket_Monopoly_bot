import numpy as np
import pytest

from saltmarket.engine.board import default_board
from saltmarket.engine.cards import default_cards
from saltmarket.engine.config import GameConfig
from saltmarket.engine.markov import (
    landing_probabilities,
    stationary_distribution,
    transition_matrix,
)
from saltmarket.sim.landing import count_visits, simulate_landings

BOARD = default_board()
CARDS = default_cards()
CONFIG = GameConfig()


def exact():
    return landing_probabilities(BOARD, CARDS, CONFIG)


def total_variation(counts):
    return np.abs(counts / counts.sum() - exact()).sum() / 2


@pytest.mark.smoke
def test_every_row_is_a_probability_distribution():
    matrix = transition_matrix(BOARD, CARDS, CONFIG)
    assert np.allclose(matrix.sum(axis=1), 1.0)
    assert (matrix >= 0).all()


@pytest.mark.smoke
def test_stationary_distribution_is_stationary():
    matrix = transition_matrix(BOARD, CARDS, CONFIG)
    pi = stationary_distribution(matrix)
    assert np.allclose(pi @ matrix, pi, atol=1e-10)
    assert pi.sum() == pytest.approx(1.0)


@pytest.mark.smoke
def test_landing_probabilities_sum_to_one():
    assert exact().sum() == pytest.approx(1.0)


@pytest.mark.smoke
def test_brig_is_most_visited_and_press_gang_is_never_a_resting_place():
    probabilities = exact()
    assert probabilities.argmax() == BOARD.brig
    assert probabilities[31] == pytest.approx(0, abs=1e-12)


@pytest.mark.smoke
def test_engine_roughly_matches_chain_on_a_short_run():
    counts = sum(count_visits(seed, turns=4000) for seed in range(5))
    assert total_variation(counts) < 0.03


@pytest.mark.slow
def test_engine_matches_chain_over_a_million_rolls():
    counts = simulate_landings(games=300, turns=4000, workers=8)
    assert counts.sum() > 1_000_000
    assert total_variation(counts) < 0.01
