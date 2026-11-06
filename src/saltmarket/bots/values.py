"""Board evaluation helpers shared by the heuristic bots."""

from collections.abc import Collection
from functools import cache

from saltmarket.engine import rules
from saltmarket.engine.board import SpaceKind, default_board
from saltmarket.engine.cards import default_cards
from saltmarket.engine.config import GameConfig
from saltmarket.engine.markov import landing_probabilities
from saltmarket.engine.state import GameState

AVERAGE_DICE = 7
ROI_BUILD_LEVEL = 3


@cache
def roi_scores() -> dict[int, float]:
    """Return expected rent per roll per coin invested for each ownable space.

    Properties are scored at three depots, ferries with the full set, and utilities
    with both owned, since that is what a strong owner aims for.
    """
    board = default_board()
    landing = landing_probabilities(board, default_cards(), GameConfig())
    scores = {}
    for index in board.ownable:
        space = board[index]
        if space.kind == SpaceKind.PROPERTY:
            income = space.rents[ROI_BUILD_LEVEL]
            cost = space.price + ROI_BUILD_LEVEL * space.build_cost
        elif space.kind == SpaceKind.FERRY:
            income, cost = space.rents[-1], space.price
        else:
            income, cost = space.rents[-1] * AVERAGE_DICE, space.price
        scores[index] = float(landing[index]) * income / cost
    return scores


def unowned_share(state: GameState) -> float:
    """Return the fraction of ownable spaces still held by the bank."""
    ownable = state.board.ownable
    return sum(state.owner[i] is None for i in ownable) / len(ownable)


def completes_group(
    state: GameState, player_id: int, index: int, also_owned: Collection[int] = ()
) -> bool:
    """Return True if gaining ``index`` would give the player its whole group."""
    group = state.board[index].group
    if group is None:
        return False
    return all(
        i == index or i in also_owned or state.owner[i] == player_id
        for i in state.board.groups[group]
    )


def blocks_rival(state: GameState, me: int, index: int) -> bool:
    """Return True if a single rival would complete a group by gaining ``index``."""
    group = state.board[index].group
    if group is None:
        return False
    others = {state.owner[i] for i in state.board.groups[group] if i != index}
    if len(others) != 1:
        return False
    rival = others.pop()
    return rival is not None and rival != me


def highest_rival_rent(state: GameState, me: int) -> int:
    """Return the largest rent any rival could charge right now."""
    return max(
        (
            rules.rent(state, i, AVERAGE_DICE)
            for i in state.board.ownable
            if state.owner[i] not in (None, me)
        ),
        default=0,
    )
