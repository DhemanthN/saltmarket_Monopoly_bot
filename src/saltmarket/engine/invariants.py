"""Conservation and consistency checks that must hold after every turn."""

from saltmarket.engine.board import SpaceKind
from saltmarket.engine.rules import PORT_LEVEL
from saltmarket.engine.state import GameState


class InvariantError(AssertionError):
    """The game state broke a rule that should be impossible to break."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvariantError(message)


def _check_money(state: GameState) -> None:
    start = state.config.starting_cash * len(state.players)
    total = sum(p.cash for p in state.players)
    _require(total == start + state.minted - state.burned, f"Money leaked: {total}")
    _require(all(p.cash >= 0 for p in state.players), "Negative cash")
    _require(state.jackpot >= 0, "Negative jackpot")


def _check_ownership(state: GameState) -> None:
    for index in range(state.board.size):
        owner = state.owner[index]
        if owner is None:
            _require(not state.mortgaged[index], f"Unowned space {index} is mortgaged")
            _require(state.level[index] == 0, f"Unowned space {index} has buildings")
        else:
            _require(state.board[index].ownable, f"Space {index} cannot be owned")
            _require(not state.players[owner].bankrupt, f"Bankrupt owner on space {index}")
    for player in state.players:
        if player.bankrupt:
            _require(player.cash == 0, f"Bankrupt player {player.id} holds cash")
            _require(not player.passes, f"Bankrupt player {player.id} holds a pass")


def _check_buildings(state: GameState) -> None:
    for group, lots in state.board.groups.items():
        levels = [state.level[i] for i in lots]
        _require(max(levels) - min(levels) <= 1, f"Uneven building in {group}")
        if max(levels):
            _require(len({state.owner[i] for i in lots}) == 1, f"Split group {group} has buildings")
            _require(not any(state.mortgaged[i] for i in lots), f"Mortgaged {group} has buildings")
    for index, space in enumerate(state.board.spaces):
        if space.kind != SpaceKind.PROPERTY:
            _require(state.level[index] == 0, f"Buildings on non-property {index}")
    ports = sum(level == PORT_LEVEL for level in state.level)
    depots = sum(level for level in state.level if level < PORT_LEVEL)
    _require(ports + state.ports_left == state.config.total_ports, "Port count mismatch")
    _require(depots + state.depots_left == state.config.total_depots, "Depot count mismatch")
    _require(state.ports_left >= 0 and state.depots_left >= 0, "Building supply below zero")


def _check_cards(state: GameState) -> None:
    for name, deck in state.decks.items():
        held = sum(card.deck == name for p in state.players for card in p.passes)
        _require(len(deck) + held == deck.size, f"Card lost from {name}")


def check_invariants(state: GameState) -> None:
    """Raise ``InvariantError`` if any game invariant is broken."""
    _check_money(state)
    _check_ownership(state)
    _check_buildings(state)
    _check_cards(state)
