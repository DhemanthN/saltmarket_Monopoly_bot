"""Trades between players: spaces, cash, and Brig passes."""

from dataclasses import dataclass

from saltmarket.engine import bank, rules
from saltmarket.engine.state import GameState, IllegalMoveError, PlayerState


@dataclass(frozen=True, slots=True)
class TradeOffer:
    """A proposed swap. "give" is what the proposer hands over, "take" what they receive."""

    proposer: int
    responder: int
    give_spaces: tuple[int, ...] = ()
    take_spaces: tuple[int, ...] = ()
    give_cash: int = 0
    take_cash: int = 0
    give_passes: int = 0
    take_passes: int = 0


def _has_buildings(state: GameState, index: int) -> bool:
    group = state.board[index].group
    return group is not None and any(state.level[i] for i in state.board.groups[group])


def _transfer_fees(state: GameState, spaces: tuple[int, ...]) -> int:
    return sum(rules.unmortgage_fee(state, i) for i in spaces if state.mortgaged[i])


def _side_is_valid(
    state: GameState,
    player: PlayerState,
    spaces: tuple[int, ...],
    cash: int,
    passes: int,
) -> bool:
    return (
        cash >= 0
        and passes >= 0
        and len(set(spaces)) == len(spaces)
        and cash <= player.cash
        and passes <= len(player.passes)
        and all(state.owner[i] == player.id and not _has_buildings(state, i) for i in spaces)
    )


def is_valid_trade(state: GameState, offer: TradeOffer) -> bool:
    """Return True if an offer follows the rules and both sides can pay for it.

    Spaces in a group with buildings cannot be traded. Whoever receives a mortgaged
    space pays the interest immediately, so each side needs cash for those fees.
    """
    if offer.proposer == offer.responder:
        return False
    proposer = state.players[offer.proposer]
    responder = state.players[offer.responder]
    if proposer.bankrupt or responder.bankrupt:
        return False
    if not (offer.give_spaces or offer.take_spaces or offer.give_cash or offer.take_cash
            or offer.give_passes or offer.take_passes):
        return False
    if not _side_is_valid(state, proposer, offer.give_spaces, offer.give_cash, offer.give_passes):
        return False
    if not _side_is_valid(state, responder, offer.take_spaces, offer.take_cash, offer.take_passes):
        return False
    proposer_cash = proposer.cash - offer.give_cash + offer.take_cash
    responder_cash = responder.cash - offer.take_cash + offer.give_cash
    return (
        proposer_cash >= _transfer_fees(state, offer.take_spaces)
        and responder_cash >= _transfer_fees(state, offer.give_spaces)
    )


def execute_trade(state: GameState, offer: TradeOffer) -> None:
    """Carry out a valid trade."""
    if not is_valid_trade(state, offer):
        raise IllegalMoveError(f"Invalid trade: {offer}")
    proposer = state.players[offer.proposer]
    responder = state.players[offer.responder]
    proposer_fees = _transfer_fees(state, offer.take_spaces)
    responder_fees = _transfer_fees(state, offer.give_spaces)
    bank.transfer(proposer, responder, offer.give_cash)
    bank.transfer(responder, proposer, offer.take_cash)
    bank.burn(state, proposer, proposer_fees)
    bank.burn(state, responder, responder_fees)
    for index in offer.give_spaces:
        state.owner[index] = responder.id
    for index in offer.take_spaces:
        state.owner[index] = proposer.id
    for _ in range(offer.give_passes):
        responder.passes.append(proposer.passes.pop())
    for _ in range(offer.take_passes):
        proposer.passes.append(responder.passes.pop())
