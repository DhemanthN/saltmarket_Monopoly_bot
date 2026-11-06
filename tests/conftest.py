import numpy as np
import pytest

from saltmarket.engine import bank
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


def set_cash(state: GameState, player_id: int, amount: int) -> None:
    """Change a player's cash through the bank so the money invariant still holds."""
    player = state.players[player_id]
    if amount > player.cash:
        bank.mint(state, player, amount - player.cash)
    else:
        bank.burn(state, player, player.cash - amount)


@pytest.fixture
def state() -> GameState:
    return make_state()
