"""Short-horizon movement forecasts from the exact Markov chain in ``engine/markov.py``.

The long-run landing probabilities say where players end up on average. These helpers
instead start from where a player stands right now and look a few rolls ahead, which is
what a bot needs to judge the rent it may owe soon or where rivals are about to land.
"""

from functools import cache

import numpy as np

from saltmarket.bots.values import AVERAGE_DICE
from saltmarket.engine import rules
from saltmarket.engine.board import default_board
from saltmarket.engine.cards import default_cards
from saltmarket.engine.config import GameConfig
from saltmarket.engine.markov import landing_probabilities, transition_matrix
from saltmarket.engine.state import GameState, PlayerState


@cache
def _chain(config: GameConfig) -> tuple[np.ndarray, np.ndarray]:
    """Return the per-roll transition matrix and a map from chain states to spaces."""
    board = default_board()
    matrix = transition_matrix(board, default_cards(), config)
    brig_base = board.size * config.max_doubles
    to_space = np.zeros((matrix.shape[0], board.size))
    for state in range(brig_base):
        to_space[state, state // config.max_doubles] = 1.0
    to_space[brig_base:, board.brig] = 1.0
    return matrix, to_space


@cache
def long_run_landing() -> np.ndarray:
    """Return the long-run chance that a roll ends on each space, for the standard rules."""
    return landing_probabilities(default_board(), default_cards(), GameConfig())


def chain_state(player: PlayerState, config: GameConfig) -> int:
    """Return the Markov chain state a player is in before their next roll."""
    if player.in_brig:
        brig_base = default_board().size * config.max_doubles
        return brig_base + min(player.brig_turns, config.max_brig_turns - 1)
    return player.position * config.max_doubles


def roll_distributions(state: GameState, player_id: int, rolls: int) -> list[np.ndarray]:
    """Return, for each of the next ``rolls`` rolls, the chance of ending on each space."""
    matrix, to_space = _chain(state.config)
    vector = np.zeros(matrix.shape[0])
    vector[chain_state(state.players[player_id], state.config)] = 1.0
    distributions = []
    for _ in range(rolls):
        vector = vector @ matrix
        distributions.append(vector @ to_space)
    return distributions


def expected_landings(state: GameState, player_id: int, rolls: int) -> np.ndarray:
    """Return the expected number of landings on each space over the next ``rolls`` rolls."""
    return np.sum(roll_distributions(state, player_id, rolls), axis=0)


def rent_owed_vector(state: GameState, player_id: int) -> np.ndarray:
    """Return the rent ``player_id`` would owe on landing on each space right now."""
    owed = np.zeros(state.board.size)
    for index in state.board.ownable:
        if state.owner[index] not in (None, player_id):
            owed[index] = rules.rent(state, index, AVERAGE_DICE)
    return owed
