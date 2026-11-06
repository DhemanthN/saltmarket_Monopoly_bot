"""Mutable game state. Per-space data lives in flat lists for speed."""

from dataclasses import dataclass, field

import numpy as np

from saltmarket.engine.board import Board
from saltmarket.engine.cards import Card, Deck
from saltmarket.engine.config import GameConfig


class IllegalMoveError(Exception):
    """A player or strategy attempted something the rules forbid."""


@dataclass(slots=True)
class PlayerState:
    """Everything that belongs to one player apart from their spaces."""

    id: int
    cash: int
    position: int = 0
    in_brig: bool = False
    brig_turns: int = 0
    passes: list[Card] = field(default_factory=list)
    bankrupt: bool = False


class GameState:
    """Full state of one game, shared by the rules, the bank, and the game loop."""

    def __init__(
        self,
        board: Board,
        cards: dict[str, tuple[Card, ...]],
        config: GameConfig,
        num_players: int,
        rng: np.random.Generator,
    ) -> None:
        """Set up a new game with shuffled decks and starting cash."""
        self.board = board
        self.config = config
        self.players = [PlayerState(i, config.starting_cash) for i in range(num_players)]
        self.decks = {name: Deck(deck, rng) for name, deck in cards.items()}
        self.owner: list[int | None] = [None] * board.size
        self.level = [0] * board.size
        self.mortgaged = [False] * board.size
        self.depots_left = config.total_depots
        self.ports_left = config.total_ports
        self.minted = 0
        self.burned = 0
        self.jackpot = 0
        self.current = 0
        self.turn = 0
        self.visits = [0] * board.size

    @property
    def alive(self) -> list[PlayerState]:
        """Return the players still in the game."""
        return [p for p in self.players if not p.bankrupt]

    def spaces_of(self, player_id: int) -> list[int]:
        """Return the indices of every space a player owns."""
        return [i for i in self.board.ownable if self.owner[i] == player_id]
