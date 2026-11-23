"""A game that narrates itself as contract events, without changing how it plays.

``ObservedGame`` only watches. Every override calls the engine's own method, the engine's
event log stays on, and no random number is drawn, so a game plays and hashes exactly as
it does without the narration.

Two kinds of event come out. Story events (roll, move, buy, rent, ...) are written when
the engine acts. State events (cash, owner, build, sell, mortgage, unmortgage) come from
comparing the board with its last snapshot, so changes the engine makes silently, such as
forced liquidation, are still reported. State events always precede the next story event.
"""

from collections.abc import Callable, Sequence
from typing import Any

from saltmarket.bots.base import Strategy
from saltmarket.engine import rules
from saltmarket.engine.actions import BrigChoice
from saltmarket.engine.cards import Card, default_cards
from saltmarket.engine.game import Game, GameResult
from saltmarket.engine.state import PlayerState
from saltmarket.engine.trade import TradeOffer
from saltmarket.rl.encoding import DecisionKind
from saltmarket.web import contract as c
from saltmarket.web.labels import offer_view
from saltmarket.web.seats import AgentSeat, HumanSeat

CARDS: dict[str, Card] = {
    card.id: card for deck in default_cards().values() for card in deck
}


class ObservedGame(Game):
    """A ``Game`` that also builds ``events``, the contract's append-only log."""

    def __init__(self, strategies: Sequence[Strategy], seed: int, **options: Any) -> None:
        """Set up the game with the engine log on, so its digest can be computed."""
        super().__init__(strategies, seed, record_log=True, **options)
        self.events: list[c.GameEvent] = []
        state = self.state
        self._cash = [p.cash for p in state.players]
        self._owner = list(state.owner)
        self._level = list(state.level)
        self._mortgaged = list(state.mortgaged)
        self._last_dice: dict[int, tuple[int, int]] = {}
        self._brig_choice: dict[int, BrigChoice] = {}
        self._story: dict[str, Callable[..., None]] = {
            "roll": self._on_roll,
            "brig_roll": self._on_roll,
            "buy": self._on_buy,
            "auction": self._on_auction,
            "trade": self._on_trade,
            "card": self._on_card,
            "to_brig": self._on_to_brig,
            "bankrupt": self._on_bankrupt,
        }
        for seat, strategy in enumerate(self.strategies):
            if isinstance(strategy, (HumanSeat, AgentSeat)):
                strategy.observer = self
            strategy.auction_bid = self._tap_bid(seat, strategy.auction_bid)
            strategy.brig_choice = self._tap_brig(seat, strategy.brig_choice)

    def record_decision(
        self, seat: int, kind: DecisionKind, action: int, explanation: c.Explanation | None
    ) -> None:
        """Log a decision a seat just made. Seats call this."""
        self._emit(
            c.DecisionMade, seat=seat, kind=kind.name.lower(), action=action,
            explanation=explanation,
        )

    def finish(self, result: GameResult) -> None:
        """Log the end of the game."""
        self._emit(
            c.GameOver, winner=result.winner, turns=result.turns, by_turn_cap=result.hit_cap
        )

    def flush(self) -> None:
        """Log every cash, ownership, building and mortgage change since the last flush."""
        state = self.state
        board = state.board
        for index in board.ownable:
            before, now = self._owner[index], state.owner[index]
            if now != before:
                self._append(c.OwnerChange, space=index, seat=now)
                self._owner[index] = now
            level, was = state.level[index], self._level[index]
            if level != was:
                seat = now if level > was else before
                self._append(
                    c.LevelChange, t="build" if level > was else "sell",
                    seat=seat if seat is not None else now, space=index, level=level,
                )
                self._level[index] = level
            mortgaged = state.mortgaged[index]
            if mortgaged != self._mortgaged[index]:
                amount = (
                    board[index].mortgage if mortgaged else rules.unmortgage_cost(state, index)
                )
                seat = now if mortgaged else before
                self._append(
                    c.MortgageChange, t="mortgage" if mortgaged else "unmortgage",
                    seat=seat if seat is not None else now, space=index, amount=amount,
                )
                self._mortgaged[index] = mortgaged
        for player in state.players:
            delta = player.cash - self._cash[player.id]
            if delta:
                self._append(c.CashChange, seat=player.id, balance=player.cash, delta=delta)
                self._cash[player.id] = player.cash

    def _append(self, event_type: type[c.EventBase], /, **fields: Any) -> None:
        self.events.append(event_type(turn=self.state.turn, seq=len(self.events), **fields))

    def _emit(self, event_type: type[c.EventBase], /, **fields: Any) -> None:
        self.flush()
        self._append(event_type, **fields)

    def _record(self, *event: object) -> None:
        super()._record(*event)
        handler = self._story.get(str(event[0]))
        if handler is None:
            self.flush()
        else:
            handler(*event[1:])

    def _on_roll(self, seat: int, first: int, second: int) -> None:
        self._last_dice[seat] = (first, second)
        self._emit(c.Roll, seat=seat, dice=(first, second))

    def _on_buy(self, seat: int, index: int) -> None:
        self._emit(c.Buy, seat=seat, space=index, price=self.state.board[index].price)

    def _on_auction(self, index: int, winner: int, price: int) -> None:
        self._emit(c.AuctionWin, seat=winner, space=index, amount=price)

    def _on_trade(self, offer: TradeOffer, accepted: bool) -> None:
        self._emit(c.TradeOffered, offer=offer_view(offer))
        self._emit(c.TradeResult, accepted=accepted)

    def _on_card(self, seat: int, card_id: str) -> None:
        card = CARDS[card_id]
        self._emit(c.CardDrawn, seat=seat, deck=card.deck, text=card.text)

    def _on_to_brig(self, seat: int) -> None:
        self._emit(c.BrigMove, t="brig_in", seat=seat)

    def _on_bankrupt(self, seat: int, creditor: int | None) -> None:
        self._emit(c.Bankrupt, seat=seat, creditor=creditor)

    def _tap_bid(self, seat: int, bid: Callable[..., int]) -> Callable[..., int]:
        def tapped(state: Any, index: int) -> int:
            amount = bid(state, index)
            if amount > 0:
                self._emit(c.AuctionBid, seat=seat, amount=amount)
            return amount

        return tapped

    def _tap_brig(self, seat: int, choose: Callable[..., BrigChoice]) -> Callable[..., BrigChoice]:
        def tapped(state: Any) -> BrigChoice:
            choice = choose(state)
            self._brig_choice[seat] = choice
            return choice

        return tapped

    def _advance(self, player: PlayerState, steps: int) -> None:
        if steps > 0:
            size = self.state.board.size
            self._emit(
                c.Move, seat=player.id,
                path=tuple((player.position + step) % size for step in range(1, steps + 1)),
                passed_home=player.position + steps >= size,
            )
        super()._advance(player, steps)

    def _card_move_relative(self, player: PlayerState, card: Card, dice_total: int) -> None:
        if card.steps < 0:
            size = self.state.board.size
            self._emit(
                c.Move, seat=player.id,
                path=tuple((player.position - step) % size for step in range(1, -card.steps + 1)),
                passed_home=False,
            )
        super()._card_move_relative(player, card, dice_total)

    def _resolve_ownable(
        self, player: PlayerState, index: int, rent_due: Callable[[], int]
    ) -> None:
        before = self.state.rent_earned[index]
        super()._resolve_ownable(player, index, rent_due)
        paid = self.state.rent_earned[index] - before
        if paid:
            self._emit(
                c.Rent, payer=player.id, payee=self.state.owner[index], space=index, amount=paid
            )

    def auction(self, index: int) -> None:
        """Run the auction and log its start, its bids, and a result even if nobody bids."""
        self._emit(c.AuctionStart, space=index)
        super().auction(index)
        if self.state.owner[index] is None:
            self._emit(c.AuctionWin, seat=None, space=index, amount=0)

    def _release(self, player: PlayerState) -> None:
        super()._release(player)
        choice = self._brig_choice.pop(player.id, BrigChoice.ROLL)
        if choice == BrigChoice.PAY:
            how = "pay"
        elif choice == BrigChoice.USE_PASS:
            how = "pass"
        else:
            first, second = self._last_dice[player.id]
            how = "roll" if first == second else "pay"
        self._emit(c.BrigMove, t="brig_out", seat=player.id, how=how)
