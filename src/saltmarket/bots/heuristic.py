"""A configurable rule-based player. Named strategies override small pieces of it."""

from collections.abc import Iterator

from saltmarket.bots.base import Strategy
from saltmarket.bots.values import blocks_rival, completes_group
from saltmarket.engine import rules
from saltmarket.engine.actions import BrigChoice, Liquidation, LiquidationKind
from saltmarket.engine.rules import PORT_LEVEL
from saltmarket.engine.state import GameState
from saltmarket.engine.trade import TradeOffer, is_valid_trade

BRIG_PASS_VALUE = 40


class HeuristicBot(Strategy):
    """Sensible defaults: buy with a cash cushion, build evenly, never trade first.

    Class attributes set the personality. Methods are the extension points that
    subclasses replace when an attribute is not enough.
    """

    name = "balanced"
    reserve = 150
    build_reserve = 200
    unmortgage_reserve = 400
    max_level = PORT_LEVEL
    bid_factor = 1.1
    proposes_trades = False
    proposes_swaps = False
    trade_premium = 1.25
    accept_margin = 1.1
    group_bonus = 1.5
    sells_buildings_first = False

    def wants(self, state: GameState, index: int) -> bool:
        """Return True if this space fits the strategy."""
        return True

    def cash_floor(self, state: GameState) -> int:
        """Return the cash to keep after buying a space."""
        return self.reserve

    def build_floor(self, state: GameState) -> int:
        """Return the cash to keep after building."""
        return self.build_reserve

    def level_cap(self, state: GameState) -> int:
        """Return the highest building level currently allowed."""
        return self.max_level

    def auction_bonus(self, state: GameState, index: int) -> int:
        """Return extra coins this strategy will pay at auction for a space."""
        return 0

    def build_choice(self, state: GameState, options: list[int]) -> int:
        """Pick where to build next. By default, the lowest level, then the priciest."""
        return min(options, key=lambda i: (state.level[i], -state.board[i].price, i))

    def _cash(self, state: GameState) -> int:
        return state.players[self.me].cash

    def should_buy(self, state: GameState, index: int) -> bool:
        """Buy wanted spaces that leave the cash floor intact."""
        price = state.board[index].price
        return self.wants(state, index) and self._cash(state) - price >= self.cash_floor(state)

    def auction_bid(self, state: GameState, index: int) -> int:
        """Bid up to a multiple of the price, without breaking the cash floor."""
        if not self.wants(state, index):
            return 0
        limit = int(state.board[index].price * self.bid_factor)
        limit += self.auction_bonus(state, index)
        return max(0, min(limit, self._cash(state) - self.cash_floor(state)))

    def choose_builds(self, state: GameState) -> Iterator[int]:
        """Build until the level cap or the cash floor stops us.

        Only lots in groups the bot owns outright can be built on, so those are the
        only candidates checked.
        """
        while True:
            sites = state.build_sites(self.me)
            if not sites:
                return
            cap = self.level_cap(state)
            spare = self._cash(state) - self.build_floor(state)
            options = [
                i for i in sites
                if state.level[i] < cap
                and state.board[i].build_cost <= spare
                and rules.can_build(state, self.me, i)
            ]
            if not options:
                return
            yield self.build_choice(state, options)

    def choose_unmortgages(self, state: GameState) -> Iterator[int]:
        """Lift mortgages, most valuable first, when cash is comfortable."""
        if not any(state.mortgaged):
            return
        mortgaged = [i for i in state.spaces_of(self.me) if state.mortgaged[i]]
        for index in sorted(mortgaged, key=lambda i: -state.board[i].price):
            cost = rules.unmortgage_cost(state, index)
            if self._cash(state) - cost >= self.unmortgage_reserve:
                yield index

    def brig_choice(self, state: GameState) -> BrigChoice:
        """Leave right away if possible, otherwise try for doubles."""
        if state.players[self.me].passes:
            return BrigChoice.USE_PASS
        if self._cash(state) >= state.config.brig_fine + self.reserve:
            return BrigChoice.PAY
        return BrigChoice.ROLL

    def raise_cash(self, state: GameState, amount: int) -> Iterator[Liquidation]:
        """Liquidate in the strategy's preferred order. The game finishes any shortfall."""
        order = (self._sell_one, self._mortgage_one)
        for step in reversed(order) if not self.sells_buildings_first else order:
            while (action := step(state)) is not None:
                yield action

    def _sell_one(self, state: GameState) -> Liquidation | None:
        for index in state.spaces_of(self.me):
            if rules.can_sell_building(state, self.me, index):
                return Liquidation(LiquidationKind.SELL_BUILDING, index)
        return None

    def _mortgage_one(self, state: GameState) -> Liquidation | None:
        options = [i for i in state.spaces_of(self.me) if rules.can_mortgage(state, self.me, i)]
        if not options:
            return None
        index = min(options, key=lambda i: (state.board[i].mortgage, i))
        return Liquidation(LiquidationKind.MORTGAGE, index)

    def _space_value(self, state: GameState, index: int, also_owned: tuple[int, ...]) -> float:
        price = state.board[index].price
        bonus = self.group_bonus if completes_group(state, self.me, index, also_owned) else 0
        return price * (1 + bonus)

    def accept_trade(self, state: GameState, offer: TradeOffer) -> bool:
        """Accept if what arrives beats what leaves, counting group completion."""
        gain = offer.give_cash + BRIG_PASS_VALUE * offer.give_passes
        gain += sum(self._space_value(state, i, offer.give_spaces) for i in offer.give_spaces)
        loss = offer.take_cash + BRIG_PASS_VALUE * offer.take_passes
        for index in offer.take_spaces:
            price = state.board[index].price
            hands_over_group = completes_group(state, offer.proposer, index, offer.take_spaces)
            loss += price * (1 + self.group_bonus) if hands_over_group else price
        return gain >= loss * self.accept_margin

    def propose_trade(self, state: GameState) -> TradeOffer | None:
        """Try to complete a group with cash, then with a swap if the bot allows it.

        Only groups split between owners can be completed by a trade, so whole groups
        are skipped without scanning their lots.
        """
        if not self.proposes_trades:
            return None
        groups = state.board.groups
        for group in state.mixed_groups():
            lots = groups[group]
            mine = [i for i in lots if state.owner[i] == self.me]
            missing = [i for i in lots if state.owner[i] != self.me]
            sellers = {state.owner[i] for i in missing}
            if not mine or not missing or len(sellers) != 1 or None in sellers:
                continue
            seller = sellers.pop()
            offer = self._cash_offer(state, seller, tuple(missing))
            if offer is None and self.proposes_swaps:
                offer = self._swap_offer(state, seller, tuple(missing))
            if offer is not None:
                return offer
        return None

    def _cash_offer(
        self, state: GameState, seller: int, wanted: tuple[int, ...]
    ) -> TradeOffer | None:
        value = sum(state.board[i].price for i in wanted)
        amount = int(value * self.trade_premium)
        if self._cash(state) - amount < self.cash_floor(state):
            return None
        offer = TradeOffer(self.me, seller, take_spaces=wanted, give_cash=amount)
        return offer if is_valid_trade(state, offer) else None

    def _swap_offer(
        self, state: GameState, seller: int, wanted: tuple[int, ...]
    ) -> TradeOffer | None:
        wanted_group = state.board[wanted[0]].group
        for index in state.spaces_of(self.me):
            group = state.board[index].group
            if group is None or group == wanted_group or completes_group(state, self.me, index):
                continue
            offer = TradeOffer(self.me, seller, give_spaces=(index,), take_spaces=wanted)
            if blocks_rival(state, self.me, index) and is_valid_trade(state, offer):
                return offer
        return None
