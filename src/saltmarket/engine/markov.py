"""Exact long-run landing probabilities, computed as a Markov chain.

Each chain state is what a player needs to know before one roll of the dice: their
position and doubles streak, or how many failed rolls they have made in the Brig. The
chain models a player who never pays to leave the Brig and holds any pass they draw,
so passes drop out of the decks. Cards are treated as uniform random draws. This is an
independent calculation from the game loop, which makes it a strong check on it.
"""

from functools import cache

import numpy as np

from saltmarket.engine.board import Board, SpaceKind
from saltmarket.engine.cards import Card, CardEffect
from saltmarket.engine.config import GameConfig

Landing = dict[tuple[int, bool], float]


def _card_destination(board: Board, position: int, card: Card) -> int | None:
    """Return where a card sends a player, None if it does not move them."""
    if card.effect == CardEffect.MOVE_TO:
        return card.target
    if card.effect == CardEffect.MOVE_RELATIVE:
        return (position + card.steps) % board.size
    if card.effect == CardEffect.NEAREST:
        candidates = board.ferries if card.space_kind == SpaceKind.FERRY else board.utilities
        return board.nearest(position, candidates)
    return None


def _landing_table(board: Board, cards: dict[str, tuple[Card, ...]]) -> list[Landing]:
    """For each space, return the chance of each (final position, in Brig) outcome."""

    @cache
    def outcomes(position: int) -> tuple[tuple[tuple[int, bool], float], ...]:
        space = board[position]
        if space.kind == SpaceKind.GO_TO_BRIG:
            return (((board.brig, True), 1.0),)
        if space.kind != SpaceKind.CARD:
            return (((position, False), 1.0),)
        deck = [c for c in cards[space.deck] if c.effect != CardEffect.BRIG_PASS]
        result: Landing = {}
        for card in deck:
            share = 1.0 / len(deck)
            if card.effect == CardEffect.GO_TO_BRIG:
                result[(board.brig, True)] = result.get((board.brig, True), 0.0) + share
                continue
            destination = _card_destination(board, position, card)
            if destination is None:
                result[(position, False)] = result.get((position, False), 0.0) + share
                continue
            for key, chance in outcomes(destination):
                result[key] = result.get(key, 0.0) + share * chance
        return tuple(result.items())

    return [dict(outcomes(position)) for position in range(board.size)]


def transition_matrix(
    board: Board, cards: dict[str, tuple[Card, ...]], config: GameConfig
) -> np.ndarray:
    """Build the per-roll transition matrix.

    States 0 to ``size * max_doubles - 1`` are free players, indexed as
    ``position * max_doubles + streak``. The last ``max_brig_turns`` states are players
    in the Brig, indexed by failed rolls so far.
    """
    streaks = config.max_doubles
    brig_base = board.size * streaks
    count = brig_base + config.max_brig_turns
    matrix = np.zeros((count, count))
    landing = _landing_table(board, cards)

    def add_landing(row: int, target: int, chance: float, streak: int) -> None:
        for (position, in_brig), share in landing[target].items():
            column = brig_base if in_brig else position * streaks + streak
            matrix[row, column] += chance * share

    faces = range(1, 7)
    for position in range(board.size):
        for streak in range(streaks):
            row = position * streaks + streak
            for first in faces:
                for second in faces:
                    target = (position + first + second) % board.size
                    if first != second:
                        add_landing(row, target, 1 / 36, 0)
                    elif streak + 1 == streaks:
                        matrix[row, brig_base] += 1 / 36
                    else:
                        add_landing(row, target, 1 / 36, streak + 1)

    for failed in range(config.max_brig_turns):
        row = brig_base + failed
        for first in faces:
            for second in faces:
                target = (board.brig + first + second) % board.size
                if first == second or failed + 1 == config.max_brig_turns:
                    add_landing(row, target, 1 / 36, 0)
                else:
                    matrix[row, row + 1] += 1 / 36
    return matrix


def stationary_distribution(matrix: np.ndarray) -> np.ndarray:
    """Solve for the long-run share of time spent in each chain state."""
    count = matrix.shape[0]
    system = np.vstack([matrix.T - np.eye(count), np.ones(count)])
    target = np.zeros(count + 1)
    target[-1] = 1.0
    return np.linalg.lstsq(system, target, rcond=None)[0]


def landing_probabilities(
    board: Board, cards: dict[str, tuple[Card, ...]], config: GameConfig
) -> np.ndarray:
    """Return the long-run chance that a roll ends on each board space."""
    stationary = stationary_distribution(transition_matrix(board, cards, config))
    brig_base = board.size * config.max_doubles
    by_space = stationary[:brig_base].reshape(board.size, config.max_doubles).sum(axis=1)
    by_space[board.brig] += stationary[brig_base:].sum()
    return by_space
