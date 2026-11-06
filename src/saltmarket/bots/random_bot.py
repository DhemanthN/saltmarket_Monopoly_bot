"""A bot that picks uniformly among legal moves, used for fuzz testing."""

from collections.abc import Iterable, Iterator

from saltmarket.bots.base import Strategy
from saltmarket.engine import rules
from saltmarket.engine.actions import BrigChoice, Liquidation, LiquidationKind
from saltmarket.engine.state import GameState
from saltmarket.engine.trade import TradeOffer, is_valid_trade


class RandomBot(Strategy):
    """Makes every decision at random from the legal options."""

    name = "random"

    def _pick(self, options: list):
        return options[int(self.rng.integers(len(options)))]

    def _chance(self, probability: float) -> bool:
        return bool(self.rng.random() < probability)

    def should_buy(self, state: GameState, index: int) -> bool:
        """Buy about two thirds of the time."""
        return self._chance(0.67)

    def auction_bid(self, state: GameState, index: int) -> int:
        """Bid a random share of current cash."""
        return int(self.rng.integers(state.players[self.me].cash + 1))

    def _legal_liquidations(self, state: GameState) -> list[Liquidation]:
        options = []
        for index in state.spaces_of(self.me):
            if rules.can_mortgage(state, self.me, index):
                options.append(Liquidation(LiquidationKind.MORTGAGE, index))
            if rules.can_sell_building(state, self.me, index):
                options.append(Liquidation(LiquidationKind.SELL_BUILDING, index))
            group = state.board[index].group
            if group and state.level[index] and rules.owns_group(state, self.me, group):
                options.append(Liquidation(LiquidationKind.SELL_GROUP, index))
        return options

    def choose_liquidations(self, state: GameState) -> Iterator[Liquidation]:
        """Occasionally sell or mortgage something for no reason."""
        while self._chance(0.1):
            options = self._legal_liquidations(state)
            if not options:
                return
            yield self._pick(options)

    def choose_unmortgages(self, state: GameState) -> Iterator[int]:
        """Unmortgage random spaces while the coin flips keep landing."""
        while self._chance(0.3):
            options = [i for i in state.spaces_of(self.me)
                       if rules.can_unmortgage(state, self.me, i)]
            if not options:
                return
            yield self._pick(options)

    def choose_builds(self, state: GameState) -> Iterator[int]:
        """Build on random legal spaces while the coin flips keep landing."""
        while self._chance(0.6):
            options = [i for i in state.spaces_of(self.me) if rules.can_build(state, self.me, i)]
            if not options:
                return
            yield self._pick(options)

    def brig_choice(self, state: GameState) -> BrigChoice:
        """Pick a random legal way out of the Brig."""
        player = state.players[self.me]
        options = [BrigChoice.ROLL]
        if player.cash >= state.config.brig_fine:
            options.append(BrigChoice.PAY)
        if player.passes:
            options.append(BrigChoice.USE_PASS)
        return self._pick(options)

    def propose_trade(self, state: GameState) -> TradeOffer | None:
        """Sometimes offer a random swap, if it happens to be valid."""
        others = [p.id for p in state.alive if p.id != self.me]
        if not others or not self._chance(0.3):
            return None
        other = self._pick(others)
        mine, theirs = state.spaces_of(self.me), state.spaces_of(other)
        offer = TradeOffer(
            self.me,
            other,
            give_spaces=(self._pick(mine),) if mine and self._chance(0.6) else (),
            take_spaces=(self._pick(theirs),) if theirs and self._chance(0.6) else (),
            give_cash=int(self.rng.integers(state.players[self.me].cash + 1) // 4),
            take_cash=int(self.rng.integers(state.players[other].cash + 1) // 4),
            give_passes=min(1, len(state.players[self.me].passes)),
        )
        return offer if is_valid_trade(state, offer) else None

    def accept_trade(self, state: GameState, offer: TradeOffer) -> bool:
        """Accept half of all offers."""
        return self._chance(0.5)

    def raise_cash(self, state: GameState, amount: int) -> Iterable[Liquidation]:
        """Liquidate random assets until the game stops asking."""
        while options := self._legal_liquidations(state):
            yield self._pick(options)
