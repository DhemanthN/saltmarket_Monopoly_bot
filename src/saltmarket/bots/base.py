"""The strategy interface. The defaults form a passive player that declines everything."""

from collections.abc import Iterable

import numpy as np

from saltmarket.engine.actions import BrigChoice, Liquidation
from saltmarket.engine.state import GameState
from saltmarket.engine.trade import TradeOffer


class Strategy:
    """Base class for all bots.

    The game calls these hooks whenever a decision is needed. Hooks that return an
    iterable are consumed lazily, so a generator sees the state after each earlier
    action was applied. Strategies must treat ``state`` as read-only. An illegal
    choice raises ``IllegalMoveError`` rather than being silently ignored.
    """

    name = "passive"

    def reset(self, player_id: int, rng: np.random.Generator) -> None:
        """Prepare for a new game in the given seat."""
        self.me = player_id
        self.rng = rng

    def should_buy(self, state: GameState, index: int) -> bool:
        """Decide whether to buy the unowned space just landed on."""
        return False

    def auction_bid(self, state: GameState, index: int) -> int:
        """Return the most this player will pay at auction, or 0 to pass."""
        return 0

    def choose_liquidations(self, state: GameState) -> Iterable[Liquidation]:
        """Yield voluntary sales or mortgages during the player's turn."""
        return ()

    def choose_unmortgages(self, state: GameState) -> Iterable[int]:
        """Yield spaces to unmortgage during the player's turn."""
        return ()

    def choose_builds(self, state: GameState) -> Iterable[int]:
        """Yield spaces to add a building level to during the player's turn."""
        return ()

    def brig_choice(self, state: GameState) -> BrigChoice:
        """Choose how to try leaving the Brig."""
        return BrigChoice.ROLL

    def propose_trade(self, state: GameState) -> TradeOffer | None:
        """Return a trade to offer, or None."""
        return None

    def accept_trade(self, state: GameState, offer: TradeOffer) -> bool:
        """Decide whether to accept a trade offered by another player."""
        return False

    def raise_cash(self, state: GameState, amount: int) -> Iterable[Liquidation]:
        """Yield sales or mortgages to cover a debt.

        If the player still cannot pay afterwards, the game liquidates the remaining
        assets in a fixed order.
        """
        return ()
