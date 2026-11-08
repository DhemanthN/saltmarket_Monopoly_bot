"""Held-out bots built around trades: mutual group swaps and flipping mortgaged land."""

import math
from collections.abc import Iterator

import numpy as np

from saltmarket.bots.forecast import long_run_landing
from saltmarket.bots.heuristic import HeuristicBot
from saltmarket.bots.values import ROI_BUILD_LEVEL, completes_group
from saltmarket.engine import rules
from saltmarket.engine.actions import Liquidation, LiquidationKind
from saltmarket.engine.state import GameState
from saltmarket.engine.trade import TradeOffer, is_valid_trade


def group_potential(state: GameState, group: str) -> float:
    """Return a group's expected rent per roll at three depots, from Markov landing rates."""
    landing = long_run_landing()
    return sum(
        float(landing[i]) * state.board[i].rents[ROI_BUILD_LEVEL]
        for i in state.board.groups[group]
    )


def missing_lots(state: GameState, group: str, holder: int, seller: int) -> tuple[int, ...]:
    """Return the lots ``holder`` lacks in a group, if ``seller`` owns all of them.

    Returns an empty tuple unless ``holder`` already owns part of the group.
    """
    lots = state.board.groups[group]
    missing = tuple(i for i in lots if state.owner[i] != holder)
    if len(missing) in (0, len(lots)) or any(state.owner[i] != seller for i in missing):
        return ()
    return missing


class SwapNegotiator(HeuristicBot):
    """Looks for swaps where both sides complete a group, balanced with cash.

    It prices the rival's view with the default HeuristicBot valuation, then adds just
    enough cash to make the deal acceptable. It only proposes when the group it gets is
    worth nearly as much rent as the group it hands over.
    """

    name = "swap_negotiator"
    proposes_trades = True
    trade_premium = 1.4
    accept_margin = 1.0
    potential_edge = 0.9

    def propose_trade(self, state: GameState) -> TradeOffer | None:
        """Prefer a mutual completion swap, else fall back to a cash offer."""
        for rival in (p.id for p in state.alive if p.id != self.me):
            for wanted_group in state.board.groups:
                want = missing_lots(state, wanted_group, self.me, rival)
                if not want:
                    continue
                for given_group in state.board.groups:
                    give = missing_lots(state, given_group, rival, self.me)
                    if not give or given_group == wanted_group:
                        continue
                    edge = group_potential(state, wanted_group) / group_potential(
                        state, given_group
                    )
                    if edge < self.potential_edge:
                        continue
                    offer = self.balanced_swap(state, rival, give, want)
                    if offer is not None:
                        return offer
        return super().propose_trade(state)

    def balanced_swap(
        self, state: GameState, rival: int, give: tuple[int, ...], want: tuple[int, ...]
    ) -> TradeOffer | None:
        """Return the swap plus the cash a default HeuristicBot needs to accept it."""
        bonus = 1 + HeuristicBot.group_bonus
        their_gain = bonus * sum(state.board[i].price for i in give)
        their_loss = bonus * sum(state.board[i].price for i in want)
        cash = max(0, math.ceil(their_loss * HeuristicBot.accept_margin - their_gain))
        if self._cash(state) - cash < self.cash_floor(state):
            return None
        offer = TradeOffer(self.me, rival, give_spaces=give, take_spaces=want, give_cash=cash)
        return offer if is_valid_trade(state, offer) else None


class MortgageFlipper(HeuristicBot):
    """Mortgages lots it cannot use, then sells them on to rivals near full price.

    Many bots value a space at list price whether or not it is mortgaged. Mortgaging
    first collects half the price from the bank, and the sale collects most of the rest
    again, so a dead lot turns into about 1.4 times its price in cash for building.
    Whether a sale went through is read from ownership afterwards, which assumes the
    engine carries out every accepted trade, as ``Game`` does.
    """

    name = "mortgage_flipper"
    flip_share = 0.9

    def reset(self, player_id: int, rng: np.random.Generator) -> None:
        """Forget the previous game's offers."""
        super().reset(player_id, rng)
        self.refused: set[tuple[int, int]] = set()
        self.pending: TradeOffer | None = None

    def is_dead(self, state: GameState, index: int) -> bool:
        """Return True for this bot's only lot in a group that a rival has started."""
        group = state.board[index].group
        if group is None:
            return False
        lots = state.board.groups[group]
        mine = rules.count_owned(state, self.me, lots)
        rival_started = any(state.owner[i] not in (None, self.me) for i in lots)
        return mine == 1 and rival_started

    def buyers(self, state: GameState, index: int) -> list[int]:
        """Return rivals not yet tried for this lot, richest first, who would not complete it."""
        rivals = [
            p.id for p in state.alive
            if p.id != self.me
            and (index, p.id) not in self.refused
            and not completes_group(state, p.id, index)
        ]
        return sorted(rivals, key=lambda r: (-state.players[r].cash, r))

    def _settle_pending(self, state: GameState) -> None:
        if self.pending is not None:
            index = self.pending.give_spaces[0]
            if state.owner[index] == self.me:
                self.refused.add((index, self.pending.responder))
            self.pending = None

    def choose_liquidations(self, state: GameState) -> Iterator[Liquidation]:
        """Mortgage dead lots that still have someone to sell them to."""
        for index in state.spaces_of(self.me):
            if (
                self.is_dead(state, index)
                and self.buyers(state, index)
                and rules.can_mortgage(state, self.me, index)
            ):
                yield Liquidation(LiquidationKind.MORTGAGE, index)

    def choose_unmortgages(self, state: GameState) -> Iterator[int]:
        """Keep flippable lots mortgaged, and lift other mortgages as usual."""
        for index in super().choose_unmortgages(state):
            if not (self.is_dead(state, index) and self.buyers(state, index)):
                yield index

    def propose_trade(self, state: GameState) -> TradeOffer | None:
        """Offer one mortgaged dead lot for cash to the richest untried rival."""
        self._settle_pending(state)
        for index in state.spaces_of(self.me):
            if not (state.mortgaged[index] and self.is_dead(state, index)):
                continue
            ask = int(state.board[index].price * self.flip_share)
            for buyer in self.buyers(state, index):
                offer = TradeOffer(self.me, buyer, give_spaces=(index,), take_cash=ask)
                if is_valid_trade(state, offer):
                    self.pending = offer
                    return offer
                self.refused.add((index, buyer))
        return None
