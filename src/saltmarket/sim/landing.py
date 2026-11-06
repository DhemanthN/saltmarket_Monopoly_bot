"""Measure landing frequencies by running the real game loop with passive players."""

import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from functools import partial

import numpy as np

from saltmarket.bots.base import Strategy
from saltmarket.engine.config import GameConfig
from saltmarket.engine.game import Game

PLAYERS_PER_GAME = 4


def count_visits(seed: int, turns: int) -> np.ndarray:
    """Return per-space end-of-roll counts from one game of passive players."""
    strategies = [Strategy() for _ in range(PLAYERS_PER_GAME)]
    game = Game(strategies, seed=seed, config=GameConfig(turn_cap=turns))
    game.play()
    return np.array(game.state.visits)


def simulate_landings(games: int, turns: int, workers: int, first_seed: int = 0) -> np.ndarray:
    """Return total end-of-roll counts per space across ``games`` seeded games."""
    seeds = range(first_seed, first_seed + games)
    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=workers, mp_context=context) as pool:
        return sum(pool.map(partial(count_visits, turns=turns), seeds, chunksize=8))
