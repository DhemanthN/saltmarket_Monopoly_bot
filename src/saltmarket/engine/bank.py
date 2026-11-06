"""All cash and building changes. Every function checks legality before acting."""

from saltmarket.engine import rules
from saltmarket.engine.rules import PORT_LEVEL
from saltmarket.engine.state import GameState, IllegalMoveError, PlayerState


def mint(state: GameState, player: PlayerState, amount: int) -> None:
    """Pay a player from the bank."""
    player.cash += amount
    state.minted += amount


def burn(state: GameState, player: PlayerState, amount: int) -> None:
    """Take money from a player into the bank."""
    if amount > player.cash:
        raise IllegalMoveError(f"Player {player.id} cannot pay {amount} with {player.cash}")
    player.cash -= amount
    state.burned += amount


def transfer(payer: PlayerState, payee: PlayerState, amount: int) -> None:
    """Move money between two players."""
    if amount > payer.cash:
        raise IllegalMoveError(f"Player {payer.id} cannot pay {amount} with {payer.cash}")
    payer.cash -= amount
    payee.cash += amount


def build(state: GameState, player_id: int, index: int) -> None:
    """Add one building level, swapping four depots for a port at the top level."""
    if not rules.can_build(state, player_id, index):
        raise IllegalMoveError(f"Player {player_id} cannot build on space {index}")
    burn(state, state.players[player_id], state.board[index].build_cost)
    state.spent[index] += state.board[index].build_cost
    state.level[index] += 1
    state.peak_level[player_id] = max(state.peak_level[player_id], state.level[index])
    if state.level[index] == PORT_LEVEL:
        state.ports_left -= 1
        state.depots_left += state.config.depots_per_port
    else:
        state.depots_left -= 1


def sell_building(state: GameState, player_id: int, index: int) -> None:
    """Remove one building level for the refund."""
    if not rules.can_sell_building(state, player_id, index):
        raise IllegalMoveError(f"Player {player_id} cannot sell on space {index}")
    if state.level[index] == PORT_LEVEL:
        state.ports_left += 1
        state.depots_left -= state.config.depots_per_port
    else:
        state.depots_left += 1
    state.level[index] -= 1
    mint(state, state.players[player_id], rules.building_refund(state, index))


def sell_group(state: GameState, player_id: int, group: str) -> None:
    """Sell every building in a group at once.

    This is always possible, even when a depot shortage blocks selling a port one
    level at a time, because the whole group ends with no buildings.
    """
    lots = state.board.groups[group]
    if not rules.owns_group(state, player_id, group):
        raise IllegalMoveError(f"Player {player_id} does not own group {group}")
    for index in lots:
        level = state.level[index]
        if level == PORT_LEVEL:
            state.ports_left += 1
        else:
            state.depots_left += level
        state.level[index] = 0
        mint(state, state.players[player_id], level * rules.building_refund(state, index))


def mortgage(state: GameState, player_id: int, index: int) -> None:
    """Mortgage a space for its mortgage value."""
    if not rules.can_mortgage(state, player_id, index):
        raise IllegalMoveError(f"Player {player_id} cannot mortgage space {index}")
    state.mortgaged[index] = True
    mint(state, state.players[player_id], state.board[index].mortgage)


def unmortgage(state: GameState, player_id: int, index: int) -> None:
    """Lift a mortgage by repaying it with interest."""
    if not rules.can_unmortgage(state, player_id, index):
        raise IllegalMoveError(f"Player {player_id} cannot unmortgage space {index}")
    burn(state, state.players[player_id], rules.unmortgage_cost(state, index))
    state.mortgaged[index] = False
