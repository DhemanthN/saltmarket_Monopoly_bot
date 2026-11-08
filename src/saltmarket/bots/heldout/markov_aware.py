"""Held-out bots that use the exact Markov chain to look ahead from the current position."""

import math
from collections.abc import Iterator

import numpy as np

from saltmarket.bots.forecast import (
    AVERAGE_DICE,
    expected_landings,
    long_run_landing,
    rent_owed_vector,
    roll_distributions,
)
from saltmarket.bots.heuristic import HeuristicBot
from saltmarket.bots.values import blocks_rival
from saltmarket.engine import rules
from saltmarket.engine.actions import BrigChoice
from saltmarket.engine.board import SpaceKind
from saltmarket.engine.state import GameState

NORMAL_95 = 1.645


def rent_at_risk(state: GameState, player_id: int, rolls: int, z: float = NORMAL_95) -> float:
    """Return a high-end estimate of the rent a player owes over their next rolls.

    Each roll's rent is a discrete distribution from the Markov chain. The estimate is
    the summed mean plus ``z`` standard deviations, treating rolls as independent.
    """
    owed = rent_owed_vector(state, player_id)
    mean = variance = 0.0
    for distribution in roll_distributions(state, player_id, rolls):
        roll_mean = float(distribution @ owed)
        mean += roll_mean
        variance += float(distribution @ owed**2) - roll_mean**2
    return mean + z * math.sqrt(max(variance, 0.0))


class RiskManager(HeuristicBot):
    """Keeps a cash reserve sized to the rent it may owe over its next two rolls."""

    name = "risk_manager"
    horizon_rolls = 2
    min_reserve = 50

    def reserve_needed(self, state: GameState) -> int:
        """Return the reserve for the current board and position."""
        risk = rent_at_risk(state, self.me, self.horizon_rolls)
        return max(self.min_reserve, math.ceil(risk))

    def cash_floor(self, state: GameState) -> int:
        """Keep the risk-based reserve after buying."""
        return self.reserve_needed(state)

    def build_floor(self, state: GameState) -> int:
        """Keep the risk-based reserve after building."""
        return self.reserve_needed(state)

    def brig_choice(self, state: GameState) -> BrigChoice:
        """Pay out only if the fine still leaves the reserve the next rolls call for."""
        if state.players[self.me].passes:
            return BrigChoice.USE_PASS
        if self._cash(state) - state.config.brig_fine >= self.reserve_needed(state):
            return BrigChoice.PAY
        return BrigChoice.ROLL


class AmbushBuilder(HeuristicBot):
    """Builds just in time, on the group rivals are about to land on.

    Each build goes where expected rival landings over the next two rolls, times the
    extra rent, per coin of building cost, is highest. It holds its cash if no rival is
    likely to land on any buildable group soon, unless it is flush.
    """

    name = "ambush_builder"
    build_reserve = 100
    horizon_rolls = 2
    ambush_chance = 0.15
    flush_cash = 800

    def rival_hits(self, state: GameState) -> np.ndarray:
        """Return expected rival landings on each space over the horizon."""
        hits = np.zeros(state.board.size)
        for player in state.alive:
            if player.id != self.me:
                hits += expected_landings(state, player.id, self.horizon_rolls)
        return hits

    def build_choice(self, state: GameState, options: list[int]) -> int:
        """Pick the best expected extra rent per coin."""
        hits = self.rival_hits(state)

        def score(index: int) -> float:
            space, level = state.board[index], state.level[index]
            return hits[index] * (space.rents[level + 1] - space.rents[level]) / space.build_cost

        return max(options, key=lambda i: (score(i), -i))

    def choose_builds(self, state: GameState) -> Iterator[int]:
        """Stop as soon as the best option's group is unlikely to be hit and cash is tight."""
        for index in super().choose_builds(state):
            group = state.board.groups[state.board[index].group]
            chance = float(self.rival_hits(state)[list(group)].sum())
            if chance < self.ambush_chance and self._cash(state) < self.flush_cash:
                return
            yield index


class NpvBidder(HeuristicBot):
    """Values each space by the rent it should earn over the rest of the game.

    Value is long-run landing chance, times rivals at the table, times the rolls left,
    times the rent expected given who holds the rest of the group, less the building
    cost. It buys when value beats the price and bids up to its value at auction, so it
    pays more at crowded tables and early on, and much less late in the game.
    """

    name = "npv_bidder"
    base_horizon = 120
    min_horizon = 20
    block_value_share = 0.5
    max_bid_multiple = 2.0
    develop_level = 3

    def horizon(self, state: GameState) -> int:
        """Return how many more rolls each rival is expected to make."""
        return max(self.min_horizon, self.base_horizon - state.turn // len(state.players))

    def expected_rent(self, state: GameState, index: int) -> tuple[float, float]:
        """Return (rent per landing, building cost) expected if this bot owns ``index``."""
        space = state.board[index]
        if space.kind == SpaceKind.FERRY:
            count = rules.count_owned(state, self.me, state.board.ferries) + 1
            return float(space.rents[count - 1]), 0.0
        if space.kind == SpaceKind.UTILITY:
            count = rules.count_owned(state, self.me, state.board.utilities) + 1
            return float(space.rents[count - 1] * AVERAGE_DICE), 0.0
        lots = state.board.groups[space.group]
        if any(state.owner[i] not in (None, self.me) for i in lots):
            return float(space.rents[0]), 0.0
        held = sum(i == index or state.owner[i] == self.me for i in lots)
        complete = held / len(lots)
        rent = complete * space.rents[self.develop_level] + (1 - complete) * space.rents[0]
        return rent, complete * self.develop_level * space.build_cost

    def value(self, state: GameState, index: int) -> float:
        """Return the space's estimated worth to this bot right now."""
        rent, build_cost = self.expected_rent(state, index)
        rivals = len(state.alive) - 1
        landings = float(long_run_landing()[index]) * rivals * self.horizon(state)
        worth = landings * rent - build_cost
        if blocks_rival(state, self.me, index):
            worth += state.board[index].price * self.block_value_share
        return worth

    def should_buy(self, state: GameState, index: int) -> bool:
        """Buy when the space is worth its price and the cash floor holds."""
        price = state.board[index].price
        return self.value(state, index) >= price and self._cash(state) - price >= self.reserve

    def auction_bid(self, state: GameState, index: int) -> int:
        """Bid the estimated value, capped by a multiple of the price and by spare cash."""
        cap = state.board[index].price * self.max_bid_multiple
        limit = int(min(self.value(state, index), cap))
        return max(0, min(limit, self._cash(state) - self.reserve))
