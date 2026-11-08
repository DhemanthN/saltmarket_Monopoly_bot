"""Measure what a player actually does, by watching its decisions during real games."""

from collections import Counter
from collections.abc import Callable, Iterable, Iterator

import numpy as np
import pandas as pd

from saltmarket.bots.base import Strategy
from saltmarket.bots.catalog import BOTS
from saltmarket.bots.registry import make_any_bot
from saltmarket.engine.actions import BrigChoice, Liquidation
from saltmarket.engine.board import SpaceKind
from saltmarket.engine.game import Game
from saltmarket.engine.state import GameState
from saltmarket.engine.trade import TradeOffer


def space_category(state: GameState, index: int) -> str:
    """Return the group name, or "ferry" or "utility" for spaces outside groups."""
    space = state.board[index]
    if space.kind == SpaceKind.FERRY:
        return "ferry"
    if space.kind == SpaceKind.UTILITY:
        return "utility"
    return space.group


class TendencyProbe(Strategy):
    """Wraps a strategy, passing every decision through while counting it by category."""

    def __init__(self, inner: Strategy, counts: Counter) -> None:
        """Watch ``inner`` and add to the shared ``counts``."""
        self.inner = inner
        self.counts = counts
        self.name = inner.name

    def reset(self, player_id: int, rng: np.random.Generator) -> None:
        """Reset both this probe and the wrapped strategy."""
        super().reset(player_id, rng)
        self.inner.reset(player_id, rng)

    def should_buy(self, state: GameState, index: int) -> bool:
        """Count purchase offers and acceptances."""
        decision = self.inner.should_buy(state, index)
        category = space_category(state, index)
        self.counts[(category, "buy_offers")] += 1
        self.counts[(category, "buys")] += int(decision)
        return decision

    def auction_bid(self, state: GameState, index: int) -> int:
        """Count bids as a share of list price."""
        bid = self.inner.auction_bid(state, index)
        category = space_category(state, index)
        self.counts[(category, "auctions_seen")] += 1
        self.counts[(category, "bid_coins")] += bid
        self.counts[(category, "bid_list_coins")] += state.board[index].price
        return bid

    def choose_builds(self, state: GameState) -> Iterator[int]:
        """Count building levels added."""
        for index in self.inner.choose_builds(state):
            self.counts[(space_category(state, index), "builds")] += 1
            yield index

    def propose_trade(self, state: GameState) -> TradeOffer | None:
        """Count trade proposals by the group wanted."""
        offer = self.inner.propose_trade(state)
        if offer is not None and offer.take_spaces:
            self.counts[(space_category(state, offer.take_spaces[0]), "trade_offers")] += 1
        return offer

    def choose_liquidations(self, state: GameState) -> Iterable[Liquidation]:
        """Pass through."""
        return self.inner.choose_liquidations(state)

    def choose_unmortgages(self, state: GameState) -> Iterable[int]:
        """Pass through."""
        return self.inner.choose_unmortgages(state)

    def brig_choice(self, state: GameState) -> BrigChoice:
        """Pass through."""
        return self.inner.brig_choice(state)

    def accept_trade(self, state: GameState, offer: TradeOffer) -> bool:
        """Pass through."""
        return self.inner.accept_trade(state, offer)

    def raise_cash(self, state: GameState, amount: int) -> Iterable[Liquidation]:
        """Pass through."""
        return self.inner.raise_cash(state, amount)


def measure_tendencies(
    make_player: Callable[[], Strategy], label: str, games: int, first_seed: int
) -> pd.DataFrame:
    """Play 2-player games against the pool and return decision rates by category."""
    counts: Counter = Counter()
    pool = sorted(BOTS)
    for offset in range(games):
        seed = first_seed + offset
        probe = TendencyProbe(make_player(), counts)
        opponent = make_any_bot(pool[offset % len(pool)])
        seats = [probe, opponent] if offset % 2 == 0 else [opponent, probe]
        Game(seats, seed=seed).play()
    categories = sorted({category for category, _ in counts})
    records = []
    for category in categories:
        offers = counts[(category, "buy_offers")]
        list_coins = counts[(category, "bid_list_coins")]
        records.append(
            {
                "player": label,
                "category": category,
                "buy_offers": offers,
                "buy_rate": counts[(category, "buys")] / offers if offers else float("nan"),
                "mean_bid_share": counts[(category, "bid_coins")] / list_coins
                if list_coins
                else float("nan"),
                "builds_per_game": counts[(category, "builds")] / games,
                "trade_offers_per_game": counts[(category, "trade_offers")] / games,
            }
        )
    return pd.DataFrame(records)


def auction_prices(name: str, table_size: int, games: int, first_seed: int) -> dict[str, float]:
    """Measure what a bot pays at auction, against random opponents from the pool."""
    pool = sorted(n for n in BOTS if n != name)
    paid = listed = wins = 0
    for offset in range(games):
        seed = first_seed + offset
        rng = np.random.default_rng(seed)
        names = [str(n) for n in rng.choice(pool, size=table_size - 1, replace=False)]
        seat = offset % table_size
        names.insert(seat, name)
        game = Game([make_any_bot(n) for n in names], seed=seed, record_log=True)
        game.play()
        for event in game.log:
            if event[0] == "auction" and event[2] == seat:
                paid += event[3]
                listed += game.state.board[event[1]].price
                wins += 1
    return {
        "bot": name,
        "table_size": table_size,
        "games": games,
        "auction_wins_per_game": wins / games,
        "share_of_list_price_paid": paid / listed if listed else float("nan"),
    }
