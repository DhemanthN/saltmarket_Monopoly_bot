"""Turns the agent's masked action ids into labelled choices a person can read."""

from bisect import bisect_right
from collections.abc import Callable

import numpy as np

from saltmarket.engine import rules
from saltmarket.engine.state import GameState
from saltmarket.engine.trade import TradeOffer
from saltmarket.rl import encoding as enc
from saltmarket.rl.encoding import Context, DecisionKind
from saltmarket.web.contract import LegalAction, TradeOfferView

PASS_LABELS = {
    DecisionKind.BUY: "Decline and send it to auction",
    DecisionKind.AUCTION: "Pass",
    DecisionKind.BUILD: "Done building",
    DecisionKind.LIQUIDATE: "Keep everything",
    DecisionKind.UNMORTGAGE: "Done",
    DecisionKind.PROPOSE: "Make no offer",
    DecisionKind.ACCEPT: "Decline",
}


def offer_view(offer: TradeOffer) -> TradeOfferView:
    """Return the JSON-friendly view of an engine trade offer."""
    return TradeOfferView(
        proposer=offer.proposer,
        responder=offer.responder,
        give_spaces=offer.give_spaces,
        take_spaces=offer.take_spaces,
        give_cash=offer.give_cash,
        take_cash=offer.take_cash,
        give_passes=offer.give_passes,
        take_passes=offer.take_passes,
    )


class _Describer:
    """Builds the label of one action id for one decision."""

    def __init__(
        self, state: GameState, me: int, kind: DecisionKind, context: Context,
        trades: dict[int, TradeOffer],
    ) -> None:
        self.state = state
        self.me = me
        self.kind = kind
        self.context = context
        self.trades = trades

    def _name(self, index: int) -> str:
        return self.state.board[index].name

    def pass_(self, action: int) -> LegalAction:
        return LegalAction(action, PASS_LABELS.get(self.kind, "Pass"))

    def yes(self, action: int) -> LegalAction:
        if self.kind == DecisionKind.BUY:
            space = self.context.space
            return LegalAction(
                action, f"Buy {self._name(space)}", self.state.board[space].price, space=space
            )
        return LegalAction(action, "Accept the offer")

    def bid(self, action: int) -> LegalAction:
        space = self.context.space
        level = enc.BID_LEVELS[action - enc.BID]
        amount = int(self.state.board[space].price * level)
        return LegalAction(action, f"Bid {amount}", amount, space=space)

    def build(self, action: int) -> LegalAction:
        group = enc.GROUPS[action - enc.BUILD]
        index = next(
            i for i in self.state.board.groups[group] if rules.can_build(self.state, self.me, i)
        )
        cost = self.state.board[index].build_cost
        return LegalAction(action, f"Build on {self._name(index)}", cost, group, index)

    def sell(self, action: int) -> LegalAction:
        group = enc.GROUPS[action - enc.SELL]
        index = next(
            i for i in self.state.board.groups[group]
            if rules.can_sell_building(self.state, self.me, i)
        )
        refund = rules.building_refund(self.state, index)
        return LegalAction(action, f"Sell a building on {self._name(index)}", refund, group, index)

    def mortgage(self, action: int) -> LegalAction:
        index = enc.OWNABLE[action - enc.MORTGAGE]
        return LegalAction(
            action, f"Mortgage {self._name(index)}", self.state.board[index].mortgage,
            self.state.board[index].group, index,
        )

    def unmortgage(self, action: int) -> LegalAction:
        index = enc.OWNABLE[action - enc.UNMORTGAGE]
        cost = rules.unmortgage_cost(self.state, index)
        return LegalAction(
            action, f"Lift the mortgage on {self._name(index)}", cost,
            self.state.board[index].group, index,
        )

    def brig(self, action: int) -> LegalAction:
        if action == enc.BRIG_PAY:
            return LegalAction(action, "Pay the fine", self.state.config.brig_fine)
        if action == enc.BRIG_PASS:
            return LegalAction(action, "Use a Brig pass")
        return LegalAction(action, "Roll for doubles")

    def trade(self, action: int) -> LegalAction:
        offer = self.trades[action]
        names = ", ".join(self._name(i) for i in offer.take_spaces)
        group = self.state.board[offer.take_spaces[0]].group
        return LegalAction(
            action, f"Offer {offer.give_cash} for {names}", offer.give_cash, group,
            offer.take_spaces[0], offer_view(offer),
        )


_STARTS: tuple[tuple[int, Callable[[_Describer, int], LegalAction]], ...] = (
    (enc.PASS, _Describer.pass_),
    (enc.YES, _Describer.yes),
    (enc.BID, _Describer.bid),
    (enc.BUILD, _Describer.build),
    (enc.SELL, _Describer.sell),
    (enc.MORTGAGE, _Describer.mortgage),
    (enc.UNMORTGAGE, _Describer.unmortgage),
    (enc.BRIG_ROLL, _Describer.brig),
    (enc.TRADE, _Describer.trade),
)
_BOUNDS = [start for start, _ in _STARTS]


def legal_actions(
    state: GameState,
    me: int,
    kind: DecisionKind,
    mask: np.ndarray,
    context: Context,
    trades: dict[int, TradeOffer],
) -> tuple[LegalAction, ...]:
    """Label every action the mask allows, in action-id order.

    ``trades`` maps trade action ids to their offers and matters only for ``PROPOSE``.
    """
    describer = _Describer(state, me, kind, context, trades)
    described = []
    for action in np.flatnonzero(mask):
        build = _STARTS[bisect_right(_BOUNDS, int(action)) - 1][1]
        described.append(build(describer, int(action)))
    return tuple(described)
