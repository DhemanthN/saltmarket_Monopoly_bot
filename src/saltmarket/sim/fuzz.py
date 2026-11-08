"""Fuzz testing: many games of random legal moves with invariants checked every turn."""

import multiprocessing
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from functools import partial

import numpy as np

from saltmarket.bots.base import Strategy
from saltmarket.bots.catalog import BOTS
from saltmarket.bots.random_bot import RandomBot
from saltmarket.bots.registry import make_any_bot
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


@dataclass(frozen=True, slots=True)
class BotFuzzSummary:
    """Totals for one bot played at mixed tables."""

    name: str
    games: int
    turns: int
    hit_cap: int
    wins: int


def fuzz_bot_seeds(
    name: str, seeds: Iterable[int], pool: Sequence[str] | None = None
) -> BotFuzzSummary:
    """Play ``name`` against random opponents from ``pool``, in a seed-chosen seat.

    The pool defaults to the training bots. Mixed tables reach far more of a bot's code
    than games against copies of itself. Any illegal move or broken invariant raises and
    stops the run.
    """
    pool = sorted(BOTS) if pool is None else sorted(pool)
    games = turns = hit_cap = wins = 0
    for seed in seeds:
        rng = np.random.default_rng(seed)
        players = 2 + seed % 3
        names = [str(n) for n in rng.choice(pool, size=players - 1)]
        seat = int(rng.integers(players))
        names.insert(seat, name)
        result = Game([make_any_bot(n) for n in names], seed=seed, debug=True).play()
        games += 1
        turns += result.turns
        hit_cap += int(result.hit_cap)
        wins += int(result.winner == seat)
    return BotFuzzSummary(name, games, turns, hit_cap, wins)


def run_bot_fuzz(
    games_per_bot: int,
    workers: int,
    first_seed: int = 0,
    names: Sequence[str] | None = None,
    pool: Sequence[str] | None = None,
) -> list[BotFuzzSummary]:
    """Fuzz each bot in ``names`` (default: the training bots) across worker processes."""
    seeds = range(first_seed, first_seed + games_per_bot)
    chunks = [seeds[i : i + CHUNK_SIZE] for i in range(0, games_per_bot, CHUNK_SIZE)]
    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=workers, mp_context=context) as executor:
        futures = {
            name: [
                executor.submit(partial(fuzz_bot_seeds, name, pool=pool), chunk)
                for chunk in chunks
            ]
            for name in (BOTS if names is None else names)
        }
        summaries = []
        for name, parts in futures.items():
            results = [part.result() for part in parts]
            summaries.append(
                BotFuzzSummary(
                    name,
                    sum(r.games for r in results),
                    sum(r.turns for r in results),
                    sum(r.hit_cap for r in results),
                    sum(r.wins for r in results),
                )
            )
    return summaries
