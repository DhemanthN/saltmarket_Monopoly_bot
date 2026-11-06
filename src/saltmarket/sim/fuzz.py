"""Fuzz testing: many games of random legal moves with invariants checked every turn."""

import multiprocessing
from collections.abc import Callable, Iterable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

from saltmarket.bots.base import Strategy
from saltmarket.bots.random_bot import RandomBot
from saltmarket.engine.game import Game

CHUNK_SIZE = 50


@dataclass(frozen=True, slots=True)
class FuzzSummary:
    """Totals from a batch of fuzz games."""

    games: int
    turns: int
    hit_cap: int

    def __add__(self, other: "FuzzSummary") -> "FuzzSummary":
        """Combine two summaries."""
        return FuzzSummary(
            self.games + other.games, self.turns + other.turns, self.hit_cap + other.hit_cap
        )


def fuzz_seeds(seeds: Iterable[int], make_bot: Callable[[], Strategy] = RandomBot) -> FuzzSummary:
    """Play one debug-mode game per seed, with 2 to 4 players chosen by the seed.

    Any illegal move or broken invariant raises and stops the run.
    """
    summary = FuzzSummary(0, 0, 0)
    for seed in seeds:
        players = 2 + seed % 3
        result = Game([make_bot() for _ in range(players)], seed=seed, debug=True).play()
        summary += FuzzSummary(1, result.turns, int(result.hit_cap))
    return summary


def run_fuzz(games: int, workers: int, first_seed: int = 0) -> FuzzSummary:
    """Run ``games`` fuzz games across worker processes using the spawn start method."""
    seeds = range(first_seed, first_seed + games)
    chunks = [seeds[i : i + CHUNK_SIZE] for i in range(0, games, CHUNK_SIZE)]
    context = multiprocessing.get_context("spawn")
    summary = FuzzSummary(0, 0, 0)
    with ProcessPoolExecutor(max_workers=workers, mp_context=context) as pool:
        for part in pool.map(fuzz_seeds, chunks):
            summary += part
    return summary
