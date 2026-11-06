"""A strategy that turns every game decision into a masked choice from the action list."""

from collections.abc import Callable, Iterator

import numpy as np

from saltmarket.bots.base import Strategy
from saltmarket.engine import rules
from saltmarket.engine.actions import BrigChoice, Liquidation, LiquidationKind
from saltmarket.engine.rules import PORT_LEVEL
from saltmarket.engine.state import GameState
from saltmarket.engine.trade import TradeOffer, is_valid_trade
from saltmarket.rl import encoding as enc
from saltmarket.rl.encoding import Context, DecisionKind

Decide = Callable[[np.ndarray, np.ndarray], int]


class AgentStrategy(Strategy):
    """Asks ``decide(observation, mask)`` for each choice.

    A decision is only requested when there is a real choice, so forced moves cost the
    agent nothing. The mask marks which entries of the action list are legal.
    """

    name = "ppo"

    def __init__(self, decide: Decide) -> None:
        """Store the function that makes decisions."""
        self.decide = decide
        self._proposed_on_turn = -1

    def reset(self, player_id: int, rng: np.random.Generator) -> None:
        """Prepare for a new game."""
        super().reset(player_id, rng)
        self._proposed_on_turn = -1

    def _ask(
        self, state: GameState, kind: DecisionKind, mask: np.ndarray, context: Context
    ) -> int:
        return self.decide(enc.encode(state, self.me, kind, context), mask)

    @staticmethod
    def _mask(*actions: int) -> np.ndarray:
        mask = np.zeros(enc.NUM_ACTIONS, dtype=bool)
        mask[list(actions)] = True
        return mask

    def _cash(self, state: GameState) -> int:
        return state.players[self.me].cash

    def should_buy(self, state: GameState, index: int) -> bool:
        """Choose whether to pay list price."""
        mask = self._mask(enc.PASS, enc.YES)
        return self._ask(state, DecisionKind.BUY, mask, Context(space=index)) == enc.YES

    def auction_bid(self, state: GameState, index: int) -> int:
        """Choose a bid as a multiple of list price."""
        price = state.board[index].price
        cash = self._cash(state)
        minimum = state.config.auction_min_bid
        legal = [
            enc.BID + slot
            for slot, level in enumerate(enc.BID_LEVELS)
            if minimum <= int(price * level) <= cash
        ]
        if not legal:
            return 0
        action = self._ask(
            state, DecisionKind.AUCTION, self._mask(enc.PASS, *legal), Context(space=index)
        )
        return 0 if action == enc.PASS else int(price * enc.BID_LEVELS[action - enc.BID])

    def _buildable(self, state: GameState, group: str) -> int | None:
        options = [
            i for i in state.board.groups[group] if rules.can_build(state, self.me, i)
        ]
        return options[0] if options else None

    def choose_builds(self, state: GameState) -> Iterator[int]:
        """Pick groups to build on, one level at a time, until the agent stops."""
        while True:
            targets = {
                enc.BUILD + slot: index
                for slot, group in enumerate(enc.GROUPS)
                if (index := self._buildable(state, group)) is not None
            }
            if not targets:
                return
            mask = self._mask(enc.PASS, *targets)
            action = self._ask(state, DecisionKind.BUILD, mask, Context())
            if action == enc.PASS:
                return
            yield targets[action]

    def choose_unmortgages(self, state: GameState) -> Iterator[int]:
        """Pick mortgages to lift until the agent stops."""
        while True:
            targets = {
                enc.UNMORTGAGE + enc.OWNABLE_SLOT[i]: i
                for i in state.spaces_of(self.me)
                if rules.can_unmortgage(state, self.me, i)
            }
            if not targets:
                return
            mask = self._mask(enc.PASS, *targets)
            action = self._ask(state, DecisionKind.UNMORTGAGE, mask, Context())
            if action == enc.PASS:
                return
            yield targets[action]

    def _liquidation_options(self, state: GameState) -> dict[int, Liquidation]:
        options = {}
        for index in state.spaces_of(self.me):
            if rules.can_mortgage(state, self.me, index):
                action = enc.MORTGAGE + enc.OWNABLE_SLOT[index]
                options[action] = Liquidation(LiquidationKind.MORTGAGE, index)
        for slot, group in enumerate(enc.GROUPS):
            sellable = [
                i for i in state.board.groups[group]
                if rules.can_sell_building(state, self.me, i)
            ]
            if sellable:
                options[enc.SELL + slot] = Liquidation(
                    LiquidationKind.SELL_BUILDING, sellable[0]
                )
        return options

    def _could_develop(self, state: GameState) -> bool:
        """Return True if the agent holds a whole unmortgaged group below port level."""
        for group, lots in state.board.groups.items():
            if (
                rules.owns_group(state, self.me, group)
                and not any(state.mortgaged[i] for i in lots)
                and min(state.level[i] for i in lots) < PORT_LEVEL
            ):
                return True
        return False

    def choose_liquidations(self, state: GameState) -> Iterator[Liquidation]:
        """Offer voluntary sales only when there is a group to fund, to avoid idle choices."""
        while self._could_develop(state):
            options = self._liquidation_options(state)
            if not options:
                return
            mask = self._mask(enc.PASS, *options)
            action = self._ask(state, DecisionKind.LIQUIDATE, mask, Context())
            if action == enc.PASS:
                return
            yield options[action]

    def raise_cash(self, state: GameState, amount: int) -> Iterator[Liquidation]:
        """Pick what to liquidate. The game stops asking once the debt is covered."""
        while options := self._liquidation_options(state):
            mask = self._mask(*options)
            action = self._ask(state, DecisionKind.RAISE_CASH, mask, Context(amount=amount))
            yield options[action]

    def brig_choice(self, state: GameState) -> BrigChoice:
        """Choose how to try leaving the Brig."""
        legal = {enc.BRIG_ROLL: BrigChoice.ROLL}
        if self._cash(state) >= state.config.brig_fine:
            legal[enc.BRIG_PAY] = BrigChoice.PAY
        if state.players[self.me].passes:
            legal[enc.BRIG_PASS] = BrigChoice.USE_PASS
        if len(legal) == 1:
            return BrigChoice.ROLL
        return legal[self._ask(state, DecisionKind.BRIG, self._mask(*legal), Context())]

    def _trade_options(self, state: GameState) -> dict[int, TradeOffer]:
        options = {}
        for slot, group in enumerate(enc.GROUPS):
            lots = state.board.groups[group]
            mine = [i for i in lots if state.owner[i] == self.me]
            missing = tuple(i for i in lots if state.owner[i] != self.me)
            sellers = {state.owner[i] for i in missing}
            if not mine or not missing or len(sellers) != 1 or None in sellers:
                continue
            seller = sellers.pop()
            value = sum(state.board[i].price for i in missing)
            for tier, premium in enumerate(enc.TRADE_PREMIUMS):
                offer = TradeOffer(
                    self.me, seller, take_spaces=missing, give_cash=int(value * premium)
                )
                if is_valid_trade(state, offer):
                    options[enc.TRADE + slot * len(enc.TRADE_PREMIUMS) + tier] = offer
        return options

    def propose_trade(self, state: GameState) -> TradeOffer | None:
        """Offer cash for the lots that complete a group, at most once per turn."""
        if state.turn == self._proposed_on_turn:
            return None
        self._proposed_on_turn = state.turn
        options = self._trade_options(state)
        if not options:
            return None
        mask = self._mask(enc.PASS, *options)
        action = self._ask(state, DecisionKind.PROPOSE, mask, Context())
        return None if action == enc.PASS else options[action]

    def accept_trade(self, state: GameState, offer: TradeOffer) -> bool:
        """Choose whether to accept an offer."""
        mask = self._mask(enc.PASS, enc.YES)
        return self._ask(state, DecisionKind.ACCEPT, mask, Context(offer=offer)) == enc.YES
