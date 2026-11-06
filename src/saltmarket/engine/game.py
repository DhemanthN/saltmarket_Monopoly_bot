"""The game loop: turns, movement, landing, cards, debts, auctions, and bankruptcy."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from saltmarket.engine import bank, rules
from saltmarket.engine.actions import BrigChoice, Liquidation, LiquidationKind
from saltmarket.engine.board import Board, SpaceKind, default_board
from saltmarket.engine.cards import Card, CardEffect, default_cards
from saltmarket.engine.config import GameConfig
from saltmarket.engine.dice import Dice, RandomDice
from saltmarket.engine.invariants import check_invariants
from saltmarket.engine.rules import PORT_LEVEL
from saltmarket.engine.state import GameState, IllegalMoveError, PlayerState
from saltmarket.engine.trade import execute_trade, is_valid_trade

if TYPE_CHECKING:
    from saltmarket.bots.base import Strategy


@dataclass(frozen=True, slots=True)
class GameResult:
    """Outcome of a finished game."""

    winner: int
    turns: int
    hit_cap: bool
    net_worths: tuple[int, ...]
    bankrupt: tuple[bool, ...]


class Game:
    """Runs one game between strategies, seat 0 moving first."""

    def __init__(
        self,
        strategies: Sequence[Strategy],
        seed: int,
        config: GameConfig | None = None,
        board: Board | None = None,
        dice: Dice | None = None,
        debug: bool = False,
        record_log: bool = False,
    ) -> None:
        """Set up a game. ``debug`` checks invariants after every turn."""
        rng = np.random.default_rng(seed)
        deck_rng, dice_rng, *bot_rngs = rng.spawn(2 + len(strategies))
        self.state = GameState(
            board or default_board(),
            default_cards(),
            config or GameConfig(),
            len(strategies),
            deck_rng,
        )
        self.strategies = list(strategies)
        for seat, (strategy, bot_rng) in enumerate(zip(self.strategies, bot_rngs, strict=True)):
            strategy.reset(seat, bot_rng)
        self.dice = dice or RandomDice(dice_rng)
        self.debug = debug
        self.log: list[tuple] | None = [] if record_log else None
        self._card_handlers: dict[CardEffect, Callable[[PlayerState, Card, int], None]] = {
            CardEffect.MOVE_TO: self._card_move_to,
            CardEffect.MOVE_RELATIVE: self._card_move_relative,
            CardEffect.NEAREST: self._card_nearest,
            CardEffect.GAIN: self._card_gain,
            CardEffect.PAY: self._card_pay,
            CardEffect.PAY_EACH: self._card_pay_each,
            CardEffect.COLLECT_EACH: self._card_collect_each,
            CardEffect.REPAIRS: self._card_repairs,
            CardEffect.GO_TO_BRIG: self._card_go_to_brig,
            CardEffect.BRIG_PASS: self._card_brig_pass,
        }

    def play(self) -> GameResult:
        """Play until one solvent player remains or the turn cap is reached."""
        state = self.state
        while not self.over and state.turn < state.config.turn_cap:
            self.take_turn(state.players[state.current])
            state.turn += 1
            if self.debug:
                check_invariants(state)
            self._advance_seat()
        return self._result()

    @property
    def over(self) -> bool:
        """Return True once at most one player is solvent."""
        return sum(not p.bankrupt for p in self.state.players) <= 1

    def _note_completed_group(self, player_id: int, index: int) -> None:
        """Record the first seat to earn a whole group.

        This runs only on purchases, auctions, and trades. Spaces inherited in a
        bankruptcy do not count, because the winner of a game inherits nearly everything
        at the moment it ends, which would make every group look decisive.
        """
        state = self.state
        group = state.board[index].group
        if (
            group is not None
            and group not in state.first_completed
            and rules.owns_group(state, player_id, group)
        ):
            state.first_completed[group] = player_id

    def _record(self, *event: object) -> None:
        if self.log is not None:
            self.log.append(event)

    def _advance_seat(self) -> None:
        state = self.state
        for offset in range(1, len(state.players) + 1):
            seat = (state.current + offset) % len(state.players)
            if not state.players[seat].bankrupt:
                state.current = seat
                return

    def _result(self) -> GameResult:
        state = self.state
        worths = tuple(rules.net_worth(state, p.id) for p in state.players)
        winner = max(state.alive, key=lambda p: (worths[p.id], -p.id)).id
        return GameResult(
            winner=winner,
            turns=state.turn,
            hit_cap=not self.over,
            net_worths=worths,
            bankrupt=tuple(p.bankrupt for p in state.players),
        )

    def take_turn(self, player: PlayerState) -> None:
        """Run one player's full turn."""
        self._manage(player)
        if player.in_brig and not self._leave_brig_voluntarily(player):
            self._roll_in_brig(player)
        else:
            self._roll_and_move(player)
        if not player.bankrupt and not self.over:
            self._manage(player)

    def _manage(self, player: PlayerState) -> None:
        """Give a player their chance to trade, liquidate, unmortgage, and build."""
        state = self.state
        strategy = self.strategies[player.id]
        for _ in range(state.config.max_trade_proposals):
            offer = strategy.propose_trade(state)
            if offer is None:
                break
            if offer.proposer != player.id or not is_valid_trade(state, offer):
                raise IllegalMoveError(f"Player {player.id} proposed invalid trade {offer}")
            accepted = self.strategies[offer.responder].accept_trade(state, offer)
            self._record("trade", offer, accepted)
            if accepted:
                execute_trade(state, offer)
                for index in offer.give_spaces:
                    self._note_completed_group(offer.responder, index)
                for index in offer.take_spaces:
                    self._note_completed_group(offer.proposer, index)
        for action in strategy.choose_liquidations(state):
            self._liquidate(player.id, action)
        for index in strategy.choose_unmortgages(state):
            bank.unmortgage(state, player.id, index)
        for index in strategy.choose_builds(state):
            bank.build(state, player.id, index)
            self._record("build", player.id, index)

    def _liquidate(self, player_id: int, action: Liquidation) -> None:
        state = self.state
        if action.kind == LiquidationKind.MORTGAGE:
            bank.mortgage(state, player_id, action.index)
        elif action.kind == LiquidationKind.SELL_BUILDING:
            bank.sell_building(state, player_id, action.index)
        else:
            group = state.board[action.index].group
            if group is None:
                raise IllegalMoveError(f"Space {action.index} is not in a group")
            bank.sell_group(state, player_id, group)
        self._record("liquidate", player_id, action.kind.value, action.index)

    def _leave_brig_voluntarily(self, player: PlayerState) -> bool:
        """Apply the player's Brig choice. Return True if they left before rolling."""
        state = self.state
        choice = self.strategies[player.id].brig_choice(state)
        if choice == BrigChoice.PAY:
            bank.burn(state, player, state.config.brig_fine)
        elif choice == BrigChoice.USE_PASS:
            if not player.passes:
                raise IllegalMoveError(f"Player {player.id} has no Brig pass")
            card = player.passes.pop()
            state.decks[card.deck].put_back(card)
        else:
            return False
        self._release(player)
        return True

    def _release(self, player: PlayerState) -> None:
        player.in_brig = False
        player.brig_turns = 0

    def _roll_in_brig(self, player: PlayerState) -> None:
        """Try for doubles. A doubles exit moves but does not earn another roll."""
        state = self.state
        first, second = self.dice.roll()
        self._record("brig_roll", player.id, first, second)
        if first != second:
            player.brig_turns += 1
            if player.brig_turns < state.config.max_brig_turns:
                state.visits[player.position] += 1
                return
            if not self.charge(player, state.config.brig_fine, None):
                return
        self._release(player)
        self._move_and_resolve(player, first + second)

    def _roll_and_move(self, player: PlayerState) -> None:
        state = self.state
        doubles = 0
        while True:
            first, second = self.dice.roll()
            self._record("roll", player.id, first, second)
            if first == second:
                doubles += 1
                if doubles == state.config.max_doubles:
                    self.send_to_brig(player)
                    state.visits[player.position] += 1
                    return
            self._move_and_resolve(player, first + second)
            if first != second or player.bankrupt or player.in_brig or self.over:
                return

    def _move_and_resolve(self, player: PlayerState, steps: int) -> None:
        self._advance(player, steps)
        self._resolve_space(player, steps)
        if not player.bankrupt:
            self.state.visits[player.position] += 1

    def _advance(self, player: PlayerState, steps: int) -> None:
        """Move forward, paying salary on passing or landing on the start space."""
        state = self.state
        position = player.position + steps
        if position >= state.board.size:
            bank.mint(state, player, state.config.salary)
        player.position = position % state.board.size

    def _advance_to(self, player: PlayerState, target: int) -> None:
        self._advance(player, (target - player.position) % self.state.board.size)

    def send_to_brig(self, player: PlayerState) -> None:
        """Move directly to the Brig without passing the start space."""
        player.position = self.state.board.brig
        player.in_brig = True
        player.brig_turns = 0
        self._record("to_brig", player.id)

    def _resolve_space(self, player: PlayerState, dice_total: int) -> None:
        state = self.state
        space = state.board[player.position]
        if space.ownable:
            self._resolve_ownable(
                player, space.index, lambda: rules.rent(state, space.index, dice_total)
            )
        elif space.kind == SpaceKind.TAX:
            if self.charge(player, space.amount, None) and state.config.calm_waters_jackpot:
                state.jackpot += space.amount
        elif space.kind == SpaceKind.CARD:
            self.apply_card(player, state.decks[space.deck].draw(), dice_total)
        elif space.kind == SpaceKind.GO_TO_BRIG:
            self.send_to_brig(player)
        elif space.kind == SpaceKind.REST and state.config.calm_waters_jackpot:
            bank.mint(state, player, state.jackpot)
            state.jackpot = 0

    def _resolve_ownable(
        self, player: PlayerState, index: int, rent_due: Callable[[], int]
    ) -> None:
        state = self.state
        owner = state.owner[index]
        if owner is None:
            self._offer_for_sale(player, index)
        elif owner != player.id:
            due = rent_due()
            if self.charge(player, due, state.players[owner]):
                state.rent_earned[index] += due

    def _offer_for_sale(self, player: PlayerState, index: int) -> None:
        state = self.state
        price = state.board[index].price
        if player.cash >= price and self.strategies[player.id].should_buy(state, index):
            bank.burn(state, player, price)
            state.owner[index] = player.id
            state.spent[index] += price
            self._note_completed_group(player.id, index)
            self._record("buy", player.id, index)
        else:
            self.auction(index)

    def auction(self, index: int) -> None:
        """Sell a space to the highest bidder.

        Each player submits their limit once. The winner pays one increment over the
        second highest limit, the same result as an open ascending auction. Ties go to
        the player seated soonest after the current player.
        """
        state = self.state
        config = state.config
        count = len(state.players)
        seats = [(state.current + offset) % count for offset in range(count)]
        bids: list[tuple[int, int]] = []
        for seat in seats:
            bidder = state.players[seat]
            if bidder.bankrupt:
                continue
            bid = self.strategies[seat].auction_bid(state, index)
            if not 0 <= bid <= bidder.cash:
                raise IllegalMoveError(f"Player {seat} bid {bid} with {bidder.cash}")
            if bid >= config.auction_min_bid:
                bids.append((bid, seat))
        if not bids:
            return
        bids.sort(key=lambda entry: -entry[0])
        top_bid, winner = bids[0]
        runner_up = bids[1][0] + config.auction_increment if len(bids) > 1 else 0
        price = min(top_bid, max(config.auction_min_bid, runner_up))
        bank.burn(state, state.players[winner], price)
        state.owner[index] = winner
        state.spent[index] += price
        self._note_completed_group(winner, index)
        self._record("auction", index, winner, price)

    def apply_card(self, player: PlayerState, card: Card, dice_total: int) -> None:
        """Carry out a drawn card."""
        self._record("card", player.id, card.id)
        self._card_handlers[card.effect](player, card, dice_total)

    def _card_move_to(self, player: PlayerState, card: Card, dice_total: int) -> None:
        self._advance_to(player, card.target)
        self._resolve_space(player, dice_total)

    def _card_move_relative(self, player: PlayerState, card: Card, dice_total: int) -> None:
        if card.steps >= 0:
            self._advance(player, card.steps)
        else:
            player.position = (player.position + card.steps) % self.state.board.size
        self._resolve_space(player, dice_total)

    def _card_nearest(self, player: PlayerState, card: Card, dice_total: int) -> None:
        state = self.state
        is_ferry = card.space_kind == SpaceKind.FERRY
        candidates = state.board.ferries if is_ferry else state.board.utilities
        index = state.board.nearest(player.position, candidates)
        self._advance_to(player, index)

        def rent_due() -> int:
            if is_ferry:
                return rules.rent(state, index, dice_total) * card.multiplier
            if state.mortgaged[index]:
                return 0
            return sum(self.dice.roll()) * card.multiplier

        self._resolve_ownable(player, index, rent_due)

    def _card_gain(self, player: PlayerState, card: Card, dice_total: int) -> None:
        bank.mint(self.state, player, card.amount)

    def _card_pay(self, player: PlayerState, card: Card, dice_total: int) -> None:
        self.charge(player, card.amount, None)

    def _card_pay_each(self, player: PlayerState, card: Card, dice_total: int) -> None:
        for other in self.state.alive:
            if other is not player and not self.charge(player, card.amount, other):
                return

    def _card_collect_each(self, player: PlayerState, card: Card, dice_total: int) -> None:
        for other in self.state.alive:
            if player.bankrupt:
                return
            if other is not player:
                self.charge(other, card.amount, player)

    def _card_repairs(self, player: PlayerState, card: Card, dice_total: int) -> None:
        state = self.state
        levels = [state.level[i] for i in state.spaces_of(player.id)]
        ports = sum(level == PORT_LEVEL for level in levels)
        depots = sum(level for level in levels if level < PORT_LEVEL)
        self.charge(player, depots * card.per_depot + ports * card.per_port, None)

    def _card_go_to_brig(self, player: PlayerState, card: Card, dice_total: int) -> None:
        self.send_to_brig(player)

    def _card_brig_pass(self, player: PlayerState, card: Card, dice_total: int) -> None:
        player.passes.append(card)

    def charge(self, player: PlayerState, amount: int, creditor: PlayerState | None) -> bool:
        """Collect a debt, liquidating if needed. Return False if the player went bankrupt.

        ``creditor`` is None when the debt is owed to the bank.
        """
        state = self.state
        if amount <= 0:
            return True
        if player.cash < amount:
            self._raise_funds(player, amount)
        if player.cash < amount:
            self._bankrupt(player, creditor)
            return False
        if creditor is None:
            bank.burn(state, player, amount)
        else:
            bank.transfer(player, creditor, amount)
        return True

    def _raise_funds(self, player: PlayerState, amount: int) -> None:
        """Let the strategy liquidate, then finish the job if it fell short."""
        state = self.state
        if player.cash + rules.liquidation_value(state, player.id) < amount:
            return
        for action in self.strategies[player.id].raise_cash(state, amount):
            if player.cash >= amount:
                return
            self._liquidate(player.id, action)
        self._force_liquidation(player, amount)

    def _force_liquidation(self, player: PlayerState, amount: int) -> None:
        """Mortgage bare spaces first, then sell buildings, then mortgage what they freed."""
        state = self.state

        def mortgage_available() -> None:
            for index in state.spaces_of(player.id):
                if player.cash < amount and rules.can_mortgage(state, player.id, index):
                    bank.mortgage(state, player.id, index)

        mortgage_available()
        for group, lots in state.board.groups.items():
            has_buildings = any(state.level[i] for i in lots)
            if player.cash < amount and has_buildings and state.owner[lots[0]] == player.id:
                bank.sell_group(state, player.id, group)
        mortgage_available()

    def _bankrupt(self, player: PlayerState, creditor: PlayerState | None) -> None:
        """Remove a player. Assets go to the creditor, or to auction if the bank is owed."""
        state = self.state
        creditor_id = None if creditor is None else creditor.id
        state.bankruptcies.append((player.id, creditor_id))
        self._record("bankrupt", player.id, creditor_id)
        for group, lots in state.board.groups.items():
            if state.owner[lots[0]] == player.id and any(state.level[i] for i in lots):
                bank.sell_group(state, player.id, group)
        spaces = state.spaces_of(player.id)
        player.bankrupt = True
        player.in_brig = False
        if creditor is None:
            self._surrender_to_bank(player, spaces)
        else:
            self._surrender_to_player(player, creditor, spaces)

    def _surrender_to_player(
        self, player: PlayerState, creditor: PlayerState, spaces: list[int]
    ) -> None:
        state = self.state
        bank.transfer(player, creditor, player.cash)
        creditor.passes.extend(player.passes)
        player.passes.clear()
        fees = 0
        for index in spaces:
            state.owner[index] = creditor.id
            if state.mortgaged[index]:
                fees += rules.unmortgage_fee(state, index)
        self.charge(creditor, fees, None)

    def _surrender_to_bank(self, player: PlayerState, spaces: list[int]) -> None:
        state = self.state
        bank.burn(state, player, player.cash)
        for card in player.passes:
            state.decks[card.deck].put_back(card)
        player.passes.clear()
        for index in spaces:
            state.owner[index] = None
            state.mortgaged[index] = False
        if not self.over:
            for index in spaces:
                self.auction(index)
