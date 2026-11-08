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


class OwnerList(list):
    """Owner of each space. Every write bumps ``version`` so ownership caches refresh."""

    def __init__(self, owners: list[int | None]) -> None:
        """Copy ``owners`` and start at version 0."""
        super().__init__(owners)
        self.version = 0

    def __setitem__(self, index: int, value: int | None) -> None:
        """Set an owner and mark every cached ownership view as stale."""
        super().__setitem__(index, value)
        self.version += 1


MIXED = object()
"""Sole-owner marker for a group whose lots have different owners."""


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
        self.owner = OwnerList([None] * board.size)
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
        self.rent_earned = [0] * board.size
        self.spent = [0] * board.size
        self.peak_level = [0] * num_players
        self.first_completed: dict[str, int] = {}
        self.bankruptcies: list[tuple[int, int | None]] = []
        self._cached_version = -1
        self._spaces: dict[int | None, tuple[int, ...]] = {}
        self._group_owner: dict[str, object] = {}
        self._mixed_groups: tuple[str, ...] = ()
        self._build_sites: dict[int | None, tuple[int, ...]] = {}

    @property
    def alive(self) -> list[PlayerState]:
        """Return the players still in the game."""
        return [p for p in self.players if not p.bankrupt]

    def spaces_of(self, player_id: int) -> list[int]:
        """Return the indices of every space a player owns, in board order."""
        if self._cached_version != self.owner.version:
            self._rebuild_ownership()
        return list(self._spaces.get(player_id, ()))

    def group_owner(self, group: str) -> object:
        """Return the player who owns every lot of a group, None, or ``MIXED``."""
        if self._cached_version != self.owner.version:
            self._rebuild_ownership()
        return self._group_owner[group]

    def mixed_groups(self) -> tuple[str, ...]:
        """Return the groups whose lots have more than one owner, the bank included."""
        if self._cached_version != self.owner.version:
            self._rebuild_ownership()
        return self._mixed_groups

    def build_sites(self, player_id: int) -> tuple[int, ...]:
        """Return the lots, in board order, of every group the player owns outright."""
        if self._cached_version != self.owner.version:
            self._rebuild_ownership()
        return self._build_sites.get(player_id, ())

    def _rebuild_ownership(self) -> None:
        """Rebuild the cached ownership views after any owner changed.

        Owners change a few dozen times per game but are queried millions of times, so
        caching them is far cheaper than scanning the board on every query.
        """
        owner = self.owner
        spaces: dict[int | None, list[int]] = {}
        for index in self.board.ownable:
            spaces.setdefault(owner[index], []).append(index)
        self._spaces = {player: tuple(indices) for player, indices in spaces.items()}
        self._group_owner = {}
        sites: dict[int | None, list[int]] = {}
        for group, lots in self.board.groups.items():
            first = owner[lots[0]]
            sole = first if all(owner[i] == first for i in lots) else MIXED
            self._group_owner[group] = sole
            if sole is not MIXED:
                sites.setdefault(sole, []).extend(lots)
        self._mixed_groups = tuple(g for g, sole in self._group_owner.items() if sole is MIXED)
        self._build_sites = {player: tuple(sorted(lots)) for player, lots in sites.items()}
        self._cached_version = owner.version
