import numpy as np
import pytest

from saltmarket.engine.board import default_board
from saltmarket.engine.cards import default_cards
from saltmarket.engine.config import GameConfig
from saltmarket.engine.state import GameState


def make_state(num_players: int = 2, **config) -> GameState:
    return GameState(
        default_board(),
        default_cards(),
        GameConfig(**config),
        num_players,
        np.random.default_rng(0),
    )


def give(state: GameState, player_id: int, *indices: int) -> None:
    for index in indices:
        state.owner[index] = player_id


@pytest.fixture
def state() -> GameState:
    return make_state()
