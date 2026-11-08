"""Held-out bots that model their rivals: progress, standing, cash, and trade history."""

from collections.abc import Collection

import numpy as np

from saltmarket.bots.heuristic import HeuristicBot
from saltmarket.engine import rules
from saltmarket.engine.state import GameState
from saltmarket.engine.trade import TradeOffer


def rival_progress(state: GameState, me: int, index: int) -> float:
    """Return the largest share of ``index``'s group held by one rival, 0 outside groups."""
    group = state.board[index].group
    if group is None:
        return 0.0
    lots = state.board.groups[group]
    best = 0.0
    for rival in {state.owner[i] for i in lots} - {None, me}:
        held = sum(state.owner[i] == rival for i in lots)
        best = max(best, held / len(lots))
    return best


def share_after_gain(state: GameState, rival: int, index: int, gained: Collection[int]) -> float:
    """Return the share of ``index``'s group ``rival`` would hold after gaining ``gained``."""
    group = state.board[index].group
    if group is None:
        return 0.0
    lots = state.board.groups[group]
    held = sum(state.owner[i] == rival or i in gained for i in lots)
    return held / len(lots)


class RivalWatcher(HeuristicBot):
    """Tracks how far each rival is into each group and contests the groups they chase."""

    name = "rival_watcher"
    contest_weight = 1.0
    contested_reserve = 0
    deny_share = 0.5

    def should_buy(self, state: GameState, index: int) -> bool:
        """Buy a space a rival is collecting even with almost no cash left."""
        if rival_progress(state, self.me, index) > 0:
            return self._cash(state) - state.board[index].price >= self.contested_reserve
        return super().should_buy(state, index)

    def auction_bonus(self, state: GameState, index: int) -> int:
        """Pay more the further a rival is into this space's group."""
        progress = rival_progress(state, self.me, index)
        return int(state.board[index].price * self.contest_weight * progress)

    def accept_trade(self, state: GameState, offer: TradeOffer) -> bool:
        """Refuse any deal that leaves the proposer holding half or more of a group."""
        gained = offer.take_spaces
        if any(
            share_after_gain(state, offer.proposer, i, gained) >= self.deny_share
            for i in gained
            if state.board[i].group is not None
        ):
            return False
        return super().accept_trade(state, offer)


class LeaderDenier(HeuristicBot):
    """Never deals with a rival who is ahead, and props up rivals who are behind."""

    name = "leader_denier"
    proposes_trades = True
    trade_premium = 1.3
    generous_margin = 0.85

    def _worth(self, state: GameState, player_id: int) -> int:
        return rules.net_worth(state, player_id)

    def is_ahead(self, state: GameState, rival: int) -> bool:
        """Return True if ``rival`` has a higher net worth than this bot."""
        return self._worth(state, rival) > self._worth(state, self.me)

    def leader(self, state: GameState) -> int | None:
        """Return the richest rival if it is ahead of this bot, else None."""
        rivals = [p.id for p in state.alive if p.id != self.me]
        if not rivals:
            return None
        richest = max(rivals, key=lambda r: (self._worth(state, r), -r))
        return richest if self.is_ahead(state, richest) else None

    def will_trade_with(self, state: GameState, seller: int) -> bool:
        """Offer trades only to rivals who are not ahead."""
        return not self.is_ahead(state, seller)

    def accept_trade(self, state: GameState, offer: TradeOffer) -> bool:
        """Refuse the leader outright. At a crowded table, give trailing rivals a discount."""
        if self.is_ahead(state, offer.proposer):
            return False
        gain, loss = self.trade_value(state, offer)
        crowded = len(state.alive) > 2
        return gain >= loss * (self.generous_margin if crowded else self.accept_margin)

    def auction_bonus(self, state: GameState, index: int) -> int:
        """Pay half again to keep the leader out of a group it has started."""
        leader = self.leader(state)
        group = state.board[index].group
        if leader is None or group is None:
            return 0
        started = any(state.owner[i] == leader for i in state.board.groups[group])
        return state.board[index].price // 2 if started else 0


class CashReader(HeuristicBot):
    """Reads rivals' cash and declines to buy when the auction is sure to be cheap."""

    name = "cash_reader"
    cheap_share = 0.8

    def richest_rival_cash(self, state: GameState) -> int:
        """Return the most cash any rival holds, which caps what it can bid."""
        return max((p.cash for p in state.alive if p.id != self.me), default=0)

    def should_buy(self, state: GameState, index: int) -> bool:
        """Send the space to auction if no rival can bid near its price, else buy it."""
        if not super().should_buy(state, index):
            return False
        price = state.board[index].price
        rival_cap = self.richest_rival_cash(state) + state.config.auction_increment
        spendable = self._cash(state) - self.cash_floor(state)
        auction_is_cheap = rival_cap < price * self.cheap_share and spendable > rival_cap
        return not auction_is_cheap


class Reciprocator(HeuristicBot):
    """Remembers who accepted its offers or offered fair deals, and trades accordingly.

    Trust starts at zero. An accepted offer or a fair incoming deal raises it, and a
    rejection or a lowball offer lowers it. Distrusted rivals get no offers and must
    beat a steep margin. Every ``forgive_turns`` game turns, grudges soften by one.

    Trust is updated inside ``accept_trade`` and from later ownership, so it assumes the
    engine carries out every trade it accepts, as ``Game`` does. Probing ``accept_trade``
    without trading would corrupt it.
    """

    name = "reciprocator"
    proposes_trades = True
    trade_premium = 1.2
    trusted_bonus = 0.15
    max_trust_bonus = 2
    fair_margin = 1.0
    grudge_margin = 1.5
    lowball_ratio = 0.8
    forgive_turns = 50

    def reset(self, player_id: int, rng: np.random.Generator) -> None:
        """Forget every rival from the previous game."""
        super().reset(player_id, rng)
        self.trust: dict[int, int] = {}
        self.pending: TradeOffer | None = None
        self.last_forgiven = 0

    def _adjust(self, rival: int, change: int) -> None:
        self.trust[rival] = self.trust.get(rival, 0) + change

    def _settle_pending(self, state: GameState) -> None:
        """Learn whether the last offer was accepted, from who owns the spaces now."""
        if self.pending is None:
            return
        accepted = all(state.owner[i] == self.me for i in self.pending.take_spaces)
        self._adjust(self.pending.responder, 1 if accepted else -1)
        self.pending = None

    def _forgive(self, state: GameState) -> None:
        if state.turn - self.last_forgiven < self.forgive_turns:
            return
        self.last_forgiven = state.turn
        for rival, trust in self.trust.items():
            if trust < 0:
                self.trust[rival] = trust + 1

    def will_trade_with(self, state: GameState, seller: int) -> bool:
        """Offer trades only to rivals it does not distrust."""
        return self.trust.get(seller, 0) >= 0

    def premium_for(self, state: GameState, seller: int) -> float:
        """Pay trusted partners a little more."""
        trust = min(max(self.trust.get(seller, 0), 0), self.max_trust_bonus)
        return self.trade_premium + self.trusted_bonus * trust

    def propose_trade(self, state: GameState) -> TradeOffer | None:
        """Update trust from the last offer, then propose like a cash trader."""
        self._settle_pending(state)
        self._forgive(state)
        offer = super().propose_trade(state)
        self.pending = offer
        return offer

    def accept_trade(self, state: GameState, offer: TradeOffer) -> bool:
        """Judge the offer, update trust in the proposer, then apply its margin."""
        gain, loss = self.trade_value(state, offer)
        if gain >= loss:
            self._adjust(offer.proposer, 1)
        elif gain < loss * self.lowball_ratio:
            self._adjust(offer.proposer, -1)
        trusted = self.trust.get(offer.proposer, 0) >= 0
        return gain >= loss * (self.fair_margin if trusted else self.grudge_margin)
