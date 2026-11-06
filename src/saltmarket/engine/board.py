"""The board: spaces, island groups, and loading from JSON."""

import json
from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[3] / "data"


class SpaceKind(StrEnum):
    """Every type of space on the board."""

    START = "start"
    PROPERTY = "property"
    FERRY = "ferry"
    UTILITY = "utility"
    CARD = "card"
    TAX = "tax"
    BRIG = "brig"
    REST = "rest"
    GO_TO_BRIG = "go_to_brig"


OWNABLE_KINDS = frozenset({SpaceKind.PROPERTY, SpaceKind.FERRY, SpaceKind.UTILITY})


@dataclass(frozen=True, slots=True)
class Space:
    """One board space. Fields that do not apply to a kind keep their defaults.

    ``rents`` means: level 0 to 5 rent for a property, rent by number owned for a
    ferry, and dice multiplier by number owned for a utility.
    """

    index: int
    name: str
    kind: SpaceKind
    group: str | None = None
    price: int = 0
    mortgage: int = 0
    build_cost: int = 0
    rents: tuple[int, ...] = ()
    amount: int = 0
    deck: str | None = None

    @property
    def ownable(self) -> bool:
        """Return True if a player can own this space."""
        return self.kind in OWNABLE_KINDS


class Board:
    """Immutable board with lookup tables built once from the space list."""

    def __init__(self, spaces: tuple[Space, ...]) -> None:
        """Index the spaces by kind and island group."""
        self.spaces = spaces
        self.size = len(spaces)
        self.groups: dict[str, tuple[int, ...]] = {}
        for space in spaces:
            if space.group is not None:
                self.groups[space.group] = (*self.groups.get(space.group, ()), space.index)
        self.ownable = tuple(s.index for s in spaces if s.ownable)
        self.ferries = self._indices(SpaceKind.FERRY)
        self.utilities = self._indices(SpaceKind.UTILITY)
        self.start = self._indices(SpaceKind.START)[0]
        self.brig = self._indices(SpaceKind.BRIG)[0]

    def _indices(self, kind: SpaceKind) -> tuple[int, ...]:
        return tuple(s.index for s in self.spaces if s.kind == kind)

    def __getitem__(self, index: int) -> Space:
        """Return the space at ``index``."""
        return self.spaces[index]

    def nearest(self, position: int, candidates: tuple[int, ...]) -> int:
        """Return the first candidate reached moving forward from ``position``."""
        return min(candidates, key=lambda index: (index - position - 1) % self.size)


def load_board(path: Path = DATA_DIR / "board.json") -> Board:
    """Load and validate a board from a JSON file."""
    raw = json.loads(path.read_text(encoding="utf-8"))["spaces"]
    spaces = tuple(
        Space(**{**entry, "kind": SpaceKind(entry["kind"]), "rents": tuple(entry.get("rents", ()))})
        for entry in raw
    )
    if [s.index for s in spaces] != list(range(len(spaces))):
        raise ValueError("Board spaces must be listed in index order starting at 0")
    return Board(spaces)


@cache
def default_board() -> Board:
    """Return the shared standard board."""
    return load_board()
