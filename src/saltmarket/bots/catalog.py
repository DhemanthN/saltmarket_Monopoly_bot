"""The named strategies. See docs/strategies.md for what each one is trying to do."""

from collections.abc import Iterator
from statistics import median

from saltmarket.bots.base import Strategy
from saltmarket.bots.heuristic import HeuristicBot
from saltmarket.bots.random_bot import RandomBot
from saltmarket.bots.values import (
    blocks_rival,
    completes_group,
    highest_rival_rent,
    roi_scores,
    spare_mortgages,
    unowned_share,
)
from saltmarket.engine import rules
from saltmarket.engine.actions import BrigChoice, Liquidation
from saltmarket.engine.board import SpaceKind
from saltmarket.engine.rules import PORT_LEVEL
from saltmarket.engine.state import GameState

EARLY_GAME_UNOWNED = 0.3
SPECIALIST_SIDE_CASH = 1500
THREE_DEPOTS = 3
PRICE_SPLIT = 200
MAX_EXPERT_RESERVE = 600


class NeverBuy(Strategy):
    """Declines every purchase, bid, and trade."""

    name = "never_buy"


class AlwaysBuy(HeuristicBot):
    """Buys whatever it can afford, with no cushion."""

    name = "always_buy"
    reserve = 0
    build_reserve = 0
    unmortgage_reserve = 200


class CashHoarder(HeuristicBot):
    """Keeps a large cash pile at all times."""

    name = "cash_hoarder"
    reserve = 500
    build_reserve = 700
    unmortgage_reserve = 800
    bid_factor = 0.9


class Specialist(HeuristicBot):
    """Chases chosen spaces, and buys others only when flush with cash."""

    name = "specialist"
    groups: frozenset[str] = frozenset()
    kinds: frozenset[SpaceKind] = frozenset()
    reserve = 50
    bid_factor = 1.5
    proposes_trades = True

    def is_target(self, state: GameState, index: int) -> bool:
        """Return True for the spaces this specialist cares about."""
        space = state.board[index]
        return space.group in self.groups or space.kind in self.kinds

    def wants(self, state: GameState, index: int) -> bool:
        """Want targets always, and anything else with plenty of spare cash."""
        spare = self._cash(state) - state.board[index].price
        return self.is_target(state, index) or spare >= SPECIALIST_SIDE_CASH


class AmberSpecialist(Specialist):
    """Focuses on the amber group just past Calm Waters."""

    name = "amber_specialist"
    groups = frozenset({"amber"})


class CinderSpecialist(Specialist):
    """Focuses on the four-lot cinder group."""

    name = "cinder_specialist"
    groups = frozenset({"cinder"})


class CoralSpecialist(Specialist):
    """Focuses on the cheap coral group just before the Brig."""

    name = "coral_specialist"
    groups = frozenset({"coral"})


class HighRoller(Specialist):
    """Focuses on the expensive jade and crown groups."""

    name = "high_roller"
    groups = frozenset({"jade", "crown"})


class FerryBaron(Specialist):
    """Collects ferries, whose rent needs no building."""

    name = "ferry_baron"
    kinds = frozenset({SpaceKind.FERRY})


class NoUtilities(HeuristicBot):
    """Buys everything except the two utilities."""

    name = "no_utilities"

    def wants(self, state: GameState, index: int) -> bool:
        """Skip utilities."""
        return state.board[index].kind != SpaceKind.UTILITY


class ThreeDepots(HeuristicBot):
    """Takes every group to three depots before going higher."""

    name = "three_depots"
    build_reserve = 120

    def level_cap(self, state: GameState) -> int:
        """Hold at three depots while any built-up group is below that level."""
        levels = [
            state.level[i]
            for i in state.spaces_of(self.me)
            if state.board[i].kind == SpaceKind.PROPERTY
            and rules.owns_group(state, self.me, state.board[i].group)
        ]
        return THREE_DEPOTS if levels and min(levels) < THREE_DEPOTS else PORT_LEVEL


class AggressiveBuilder(HeuristicBot):
    """Spends everything on buildings, mortgaging spare spaces to fund them."""

    name = "aggressive_builder"
    reserve = 50
    build_reserve = 0
    unmortgage_reserve = 900

    def choose_liquidations(self, state: GameState) -> Iterator[Liquidation]:
        """Mortgage spaces outside completed groups when a group could be built on."""
        return spare_mortgages(state, self.me)


class PortRush(HeuristicBot):
    """Finishes one group to ports before starting another."""

    name = "port_rush"
    build_reserve = 80

    def build_choice(self, state: GameState, options: list[int]) -> int:
        """Stay on the most developed group."""
        def group_level(index: int) -> int:
            return sum(state.level[i] for i in state.board.groups[state.board[index].group])

        return max(options, key=lambda i: (group_level(i), state.board[i].price, -i))


class ShortageBlocker(HeuristicBot):
    """Stops at four depots so the depot supply stays tied up."""

    name = "shortage_blocker"
    max_level = PORT_LEVEL - 1
    build_reserve = 120


class BrigStayer(HeuristicBot):
    """Sits in the Brig late in the game, collecting rent while rivals circle."""

    name = "brig_stayer"

    def brig_choice(self, state: GameState) -> BrigChoice:
        """Never pay or use a pass once the board is mostly sold."""
        if unowned_share(state) < EARLY_GAME_UNOWNED:
            return BrigChoice.ROLL
        return super().brig_choice(state)


class RoiBuyer(HeuristicBot):
    """Buys only spaces with above-median expected return."""

    name = "roi_buyer"
    bid_factor = 1.25

    def wants(self, state: GameState, index: int) -> bool:
        """Compare this space's score with the median across the board."""
        scores = roi_scores()
        return scores[index] >= median(scores.values())


class AggressiveTrader(HeuristicBot):
    """Pays well over face value and swaps freely to complete groups."""

    name = "aggressive_trader"
    proposes_trades = True
    proposes_swaps = True
    trade_premium = 1.75
    accept_margin = 0.95


class MonopolyTrader(HeuristicBot):
    """Trades only to complete groups, and resists completing anyone else's."""

    name = "monopoly_trader"
    proposes_trades = True
    trade_premium = 1.3
    accept_margin = 1.25
    group_bonus = 2.5


class AuctionSniper(HeuristicBot):
    """Refuses list price and hopes to win spaces cheaply at auction."""

    name = "auction_sniper"
    bid_factor = 0.75

    def should_buy(self, state: GameState, index: int) -> bool:
        """Decline every purchase, sending the space to auction."""
        return False


class ConservativeMortgager(HeuristicBot):
    """Avoids mortgages, selling buildings first and repaying debt quickly."""

    name = "conservative_mortgager"
    reserve = 250
    unmortgage_reserve = 100
    sells_buildings_first = True


class GroupBlocker(HeuristicBot):
    """Pays heavily to deny rivals a completed group."""

    name = "group_blocker"
    accept_margin = 1.3

    def auction_bonus(self, state: GameState, index: int) -> int:
        """Add the full price when winning stops a rival's group."""
        return state.board[index].price if blocks_rival(state, self.me, index) else 0


class CheapLots(HeuristicBot):
    """Buys only low-priced spaces, then builds early."""

    name = "cheap_lots"
    build_reserve = 100

    def wants(self, state: GameState, index: int) -> bool:
        """Want spaces at or below the price split."""
        return state.board[index].price <= PRICE_SPLIT


class PremiumLots(HeuristicBot):
    """Buys only high-priced spaces."""

    name = "premium_lots"

    def wants(self, state: GameState, index: int) -> bool:
        """Want spaces at or above the price split."""
        return state.board[index].price >= PRICE_SPLIT


class RentMaximizer(HeuristicBot):
    """Builds wherever one more level adds the most rent per coin."""

    name = "rent_maximizer"
    build_reserve = 120

    def build_choice(self, state: GameState, options: list[int]) -> int:
        """Pick the best marginal rent per building cost."""
        def marginal(index: int) -> float:
            space, level = state.board[index], state.level[index]
            return (space.rents[level + 1] - space.rents[level]) / space.build_cost

        return max(options, key=lambda i: (marginal(i), -i))


class Expert(BrigStayer):
    """Combines the best ideas and sizes its reserve to the threat on the board."""

    name = "expert"
    bid_factor = 1.3
    proposes_trades = True
    proposes_swaps = True
    trade_premium = 1.4
    accept_margin = 1.2
    group_bonus = 2.0

    def cash_floor(self, state: GameState) -> int:
        """Spend freely early, then keep enough to survive the worst rent."""
        if unowned_share(state) >= EARLY_GAME_UNOWNED:
            return 50
        return min(MAX_EXPERT_RESERVE, max(100, highest_rival_rent(state, self.me)))

    def build_floor(self, state: GameState) -> int:
        """Build with a cushion matched to the current threat."""
        return min(MAX_EXPERT_RESERVE, max(80, highest_rival_rent(state, self.me) // 2))

    def auction_bonus(self, state: GameState, index: int) -> int:
        """Pay extra to finish a group or to stop a rival finishing one."""
        price = state.board[index].price
        if completes_group(state, self.me, index):
            return price
        return price // 2 if blocks_rival(state, self.me, index) else 0


ALL_BOTS: tuple[type[Strategy], ...] = (
    RandomBot, NeverBuy, AlwaysBuy, HeuristicBot, CashHoarder, AmberSpecialist,
    CinderSpecialist, CoralSpecialist, HighRoller, FerryBaron, NoUtilities, ThreeDepots,
    AggressiveBuilder, PortRush, ShortageBlocker, BrigStayer, RoiBuyer, AggressiveTrader,
    MonopolyTrader, AuctionSniper, ConservativeMortgager, GroupBlocker, CheapLots,
    PremiumLots, RentMaximizer, Expert,
)
BOTS: dict[str, type[Strategy]] = {bot.name: bot for bot in ALL_BOTS}


def make_bot(name: str) -> Strategy:
    """Create a new bot by name."""
    return BOTS[name]()
