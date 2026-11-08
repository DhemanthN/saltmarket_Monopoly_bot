"""Held-out bots that switch their whole personality as the game state changes.

Each bot picks a ``Posture`` before every decision. A posture bundles the settings a
``HeuristicBot`` reads, so one bot can play like a reckless buyer in one turn and a
careful saver in the next.
"""

from collections.abc import Iterable
from dataclasses import dataclass, fields

from saltmarket.bots.heuristic import HeuristicBot
from saltmarket.bots.values import (
    AVERAGE_DICE,
    blocks_rival,
    spare_mortgages,
    unowned_share,
)
from saltmarket.engine import rules
from saltmarket.engine.actions import BrigChoice, Liquidation
from saltmarket.engine.board import SpaceKind
from saltmarket.engine.state import GameState
from saltmarket.engine.trade import TradeOffer


@dataclass(frozen=True, slots=True)
class Posture:
    """A set of HeuristicBot settings. Defaults match the plain ``balanced`` bot."""

    reserve: int = HeuristicBot.reserve
    build_reserve: int = HeuristicBot.build_reserve
    unmortgage_reserve: int = HeuristicBot.unmortgage_reserve
    bid_factor: float = HeuristicBot.bid_factor
    proposes_trades: bool = False
    proposes_swaps: bool = False
    trade_premium: float = HeuristicBot.trade_premium
    accept_margin: float = HeuristicBot.accept_margin
    leverage: bool = False


BALANCED = Posture()


class AdaptiveBot(HeuristicBot):
    """A HeuristicBot that adopts a fresh posture at the start of every decision."""

    name = "adaptive"
    leverage = False

    def posture(self, state: GameState) -> Posture:
        """Return the posture to play with right now."""
        return BALANCED

    def _adopt(self, state: GameState) -> None:
        current = self.posture(state)
        for field in fields(current):
            setattr(self, field.name, getattr(current, field.name))

    def should_buy(self, state: GameState, index: int) -> bool:
        """Decide with the current posture."""
        self._adopt(state)
        return super().should_buy(state, index)

    def auction_bid(self, state: GameState, index: int) -> int:
        """Bid with the current posture."""
        self._adopt(state)
        return super().auction_bid(state, index)

    def choose_liquidations(self, state: GameState) -> Iterable[Liquidation]:
        """Mortgage spare spaces to fund building when the posture calls for leverage."""
        self._adopt(state)
        return spare_mortgages(state, self.me) if self.leverage else ()

    def choose_unmortgages(self, state: GameState) -> Iterable[int]:
        """Unmortgage with the current posture."""
        self._adopt(state)
        return super().choose_unmortgages(state)

    def choose_builds(self, state: GameState) -> Iterable[int]:
        """Build with the current posture."""
        self._adopt(state)
        return super().choose_builds(state)

    def brig_choice(self, state: GameState) -> BrigChoice:
        """Leave the Brig with the current posture."""
        self._adopt(state)
        return super().brig_choice(state)

    def propose_trade(self, state: GameState) -> TradeOffer | None:
        """Propose with the current posture."""
        self._adopt(state)
        return super().propose_trade(state)

    def accept_trade(self, state: GameState, offer: TradeOffer) -> bool:
        """Respond with the current posture."""
        self._adopt(state)
        return super().accept_trade(state, offer)

    def raise_cash(self, state: GameState, amount: int) -> Iterable[Liquidation]:
        """Raise cash with the current posture."""
        self._adopt(state)
        return super().raise_cash(state, amount)


def owns_any_group(state: GameState, player_id: int) -> bool:
    """Return True if the player owns a whole island group."""
    return any(rules.owns_group(state, player_id, group) for group in state.board.groups)


class PhaseShifter(AdaptiveBot):
    """Grabs land, then trades to finish a group, then pours everything into building."""

    name = "phase_shifter"
    grab_until_unowned = 0.5
    GRAB = Posture(reserve=0, build_reserve=0, bid_factor=1.0)
    CONSOLIDATE = Posture(
        reserve=100, build_reserve=150, bid_factor=1.2, proposes_trades=True,
        proposes_swaps=True, trade_premium=1.6, accept_margin=1.0,
    )
    DEVELOP = Posture(
        reserve=100, build_reserve=50, unmortgage_reserve=600, bid_factor=1.0,
        accept_margin=1.4, leverage=True,
    )

    def posture(self, state: GameState) -> Posture:
        """Develop once a group is held, grab while land is plentiful, else consolidate."""
        if owns_any_group(state, self.me):
            return self.DEVELOP
        if unowned_share(state) >= self.grab_until_unowned:
            return self.GRAB
        return self.CONSOLIDATE

    def wants(self, state: GameState, index: int) -> bool:
        """While consolidating, buy only spaces that advance a group or block a rival."""
        if self.posture(state) is not self.CONSOLIDATE:
            return True
        group = state.board[index].group
        if group is None:
            return False
        holds_lot = any(state.owner[i] == self.me for i in state.board.groups[group])
        return holds_lot or blocks_rival(state, self.me, index)


class ScoreAware(AdaptiveBot):
    """Plays safe while ahead on net worth and takes big risks while behind."""

    name = "score_aware"
    band = 0.15
    PROTECT = Posture(
        reserve=350, build_reserve=300, unmortgage_reserve=500, bid_factor=1.0,
        accept_margin=1.5,
    )
    GAMBLE = Posture(
        reserve=0, build_reserve=0, unmortgage_reserve=900, bid_factor=1.4,
        proposes_trades=True, proposes_swaps=True, trade_premium=1.6, accept_margin=0.95,
        leverage=True,
    )

    def share(self, state: GameState) -> float:
        """Return this bot's share of the net worth of every player still in the game."""
        worths = {p.id: rules.net_worth(state, p.id) for p in state.alive}
        total = sum(worths.values())
        return worths[self.me] / total if total else 0.0

    def posture(self, state: GameState) -> Posture:
        """Compare the share with an even split of the table."""
        fair = 1 / len(state.alive)
        share = self.share(state)
        if share >= fair * (1 + self.band):
            return self.PROTECT
        if share <= fair * (1 - self.band):
            return self.GAMBLE
        return BALANCED


class Finisher(AdaptiveBot):
    """Waits patiently, then goes all in once a rival is close to bankruptcy."""

    name = "finisher"
    strike_multiple = 2.0
    PATIENT = Posture(
        reserve=250, build_reserve=250, bid_factor=1.1, proposes_trades=True,
        trade_premium=1.4, accept_margin=1.2,
    )
    CLOSE = Posture(
        reserve=0, build_reserve=0, unmortgage_reserve=900, bid_factor=0.8,
        accept_margin=1.5, leverage=True,
    )

    def my_threat(self, state: GameState) -> int:
        """Return the largest rent this bot could charge right now."""
        return max(
            (rules.rent(state, i, AVERAGE_DICE) for i in state.spaces_of(self.me)), default=0
        )

    def rival_in_reach(self, state: GameState) -> bool:
        """Return True if some rival could not survive a couple of this bot's rents."""
        threat = self.my_threat(state)
        if threat == 0:
            return False
        return any(
            p.cash + rules.liquidation_value(state, p.id) < threat * self.strike_multiple
            for p in state.alive
            if p.id != self.me
        )

    def posture(self, state: GameState) -> Posture:
        """Close out the game when a rival is weak, otherwise build patiently."""
        return self.CLOSE if self.rival_in_reach(state) else self.PATIENT

    def brig_choice(self, state: GameState) -> BrigChoice:
        """While closing, sit in the Brig so the weak rival keeps circling the board."""
        if self.rival_in_reach(state) and self._owns_rent_earners(state):
            return BrigChoice.ROLL
        return super().brig_choice(state)

    def _owns_rent_earners(self, state: GameState) -> bool:
        return any(
            state.board[i].kind == SpaceKind.PROPERTY and not state.mortgaged[i]
            for i in state.spaces_of(self.me)
        )
