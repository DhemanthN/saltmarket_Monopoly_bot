"""Dice. Kept separate so tests can substitute scripted rolls."""

from typing import Protocol

import numpy as np


class Dice(Protocol):
    """Anything that can produce a roll of two dice."""

    def roll(self) -> tuple[int, int]:
        """Return the two die faces."""
        ...


class RandomDice:
    """Fair six-sided dice driven by a seeded generator."""

    def __init__(self, rng: np.random.Generator) -> None:
        """Store the generator used for every roll."""
        self._rng = rng

    def roll(self) -> tuple[int, int]:
        """Return two independent faces from 1 to 6."""
        first, second = self._rng.integers(1, 7, size=2)
        return int(first), int(second)
