"""Read-only rule queries. Nothing in this module changes the game state."""

import math

from saltmarket.engine.board import SpaceKind
from saltmarket.engine.state import GameState

PORT_LEVEL = 5


def owns_group(state: GameState, player_id: int, group: str) -> bool:
    """Return True if the player owns every lot in an island group."""
    return all(state.owner[i] == player_id for i in state.board.groups[group])


def count_owned(state: GameState, player_id: int, indices: tuple[int, ...]) -> int:
    """Return how many of ``indices`` the player owns."""
    return sum(state.owner[i] == player_id for i in indices)


def rent(state: GameState, index: int, dice_total: int) -> int:
    """Return the rent owed for landing on an owned space. Mortgaged spaces pay nothing."""
    owner = state.owner[index]
    if owner is None or state.mortgaged[index]:
        return 0
    space = state.board[index]
    if space.kind == SpaceKind.FERRY:
        return space.rents[count_owned(state, owner, state.board.ferries) - 1]
    if space.kind == SpaceKind.UTILITY:
        return space.rents[count_owned(state, owner, state.board.utilities) - 1] * dice_total
    level = state.level[index]
    if level == 0 and owns_group(state, owner, space.group):
        return space.rents[0] * state.config.group_rent_multiplier
    return space.rents[level]


def unmortgage_fee(state: GameState, index: int) -> int:
    """Return the interest on a mortgaged space, rounded up to a whole coin."""
    interest = state.board[index].mortgage * state.config.mortgage_interest
    return math.ceil(round(interest, 6))


def unmortgage_cost(state: GameState, index: int) -> int:
    """Return the mortgage value plus interest."""
    return state.board[index].mortgage + unmortgage_fee(state, index)


def building_refund(state: GameState, index: int) -> int:
    """Return the cash received for selling one building level on a space."""
    return int(state.board[index].build_cost * state.config.building_sale_fraction)


def can_build(state: GameState, player_id: int, index: int) -> bool:
    """Return True if the player may add one building level to a space."""
    space = state.board[index]
    if space.kind != SpaceKind.PROPERTY or state.owner[index] != player_id:
        return False
    if not owns_group(state, player_id, space.group):
        return False
    lots = state.board.groups[space.group]
    if any(state.mortgaged[i] for i in lots):
        return False
    level = state.level[index]
    if level >= PORT_LEVEL or level != min(state.level[i] for i in lots):
        return False
    supply = state.ports_left if level == PORT_LEVEL - 1 else state.depots_left
    return supply > 0 and state.players[player_id].cash >= space.build_cost


def can_sell_building(state: GameState, player_id: int, index: int) -> bool:
    """Return True if the player may remove one building level from a space."""
    if state.owner[index] != player_id or state.level[index] == 0:
        return False
    level = state.level[index]
    lots = state.board.groups[state.board[index].group]
    if level != max(state.level[i] for i in lots):
        return False
    return level < PORT_LEVEL or state.depots_left >= state.config.depots_per_port


def can_mortgage(state: GameState, player_id: int, index: int) -> bool:
    """Return True if the player may mortgage a space."""
    if state.owner[index] != player_id or state.mortgaged[index]:
        return False
    group = state.board[index].group
    return group is None or not any(state.level[i] for i in state.board.groups[group])


def can_unmortgage(state: GameState, player_id: int, index: int) -> bool:
    """Return True if the player may lift the mortgage on a space."""
    return (
        state.owner[index] == player_id
        and state.mortgaged[index]
        and state.players[player_id].cash >= unmortgage_cost(state, index)
    )


def liquidation_value(state: GameState, player_id: int) -> int:
    """Return the cash a player could raise by selling and mortgaging everything."""
    total = 0
    for index in state.spaces_of(player_id):
        if state.level[index]:
            total += state.level[index] * building_refund(state, index)
        if not state.mortgaged[index]:
            total += state.board[index].mortgage
    return total


def net_worth(state: GameState, player_id: int) -> int:
    """Return cash plus spaces at face value plus buildings at cost."""
    total = state.players[player_id].cash
    for index in state.spaces_of(player_id):
        space = state.board[index]
        total += space.mortgage if state.mortgaged[index] else space.price
        total += state.level[index] * space.build_cost
    return total
