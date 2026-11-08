"""Dice. Kept separate so tests can substitute scripted rolls."""

from typing import Protocol

import numpy as np

BATCH_ROLLS = 512


class Dice(Protocol):
    """Anything that can produce a roll of two dice."""

    def roll(self) -> tuple[int, int]:
        """Return the two die faces."""
        ...


class RandomDice:
    """Fair six-sided dice driven by a seeded generator.

    Faces are drawn from the generator in batches, which is far cheaper than one NumPy
    call per roll. NumPy produces the same stream of faces whether they are drawn one
    at a time or in a batch, so games are identical either way. The generator must
    belong to these dice alone, because a batch draws ahead of the current roll.
    """

    def __init__(self, rng: np.random.Generator) -> None:
        """Store the generator used for every roll."""
        self._rng = rng
        self._faces: list[int] = []
        self._next = 0

    def roll(self) -> tuple[int, int]:
        """Return two independent faces from 1 to 6."""
        position = self._next
        if position == len(self._faces):
            self._faces = self._rng.integers(1, 7, size=2 * BATCH_ROLLS).tolist()
            position = 0
        self._next = position + 2
        return self._faces[position], self._faces[position + 1]
