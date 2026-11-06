"""Tide and Ledger cards, and the decks that cycle them."""

import json
from collections import deque
from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from pathlib import Path

import numpy as np

from saltmarket.engine.board import DATA_DIR, SpaceKind


class CardEffect(StrEnum):
    """What a card does when drawn."""

    MOVE_TO = "move_to"
    MOVE_RELATIVE = "move_relative"
    NEAREST = "nearest"
    GAIN = "gain"
    PAY = "pay"
    PAY_EACH = "pay_each"
    COLLECT_EACH = "collect_each"
    REPAIRS = "repairs"
    GO_TO_BRIG = "go_to_brig"
    BRIG_PASS = "brig_pass"


@dataclass(frozen=True, slots=True)
class Card:
    """One card. Fields that do not apply to an effect keep their defaults."""

    id: str
    deck: str
    text: str
    effect: CardEffect
    target: int = 0
    steps: int = 0
    amount: int = 0
    per_depot: int = 0
    per_port: int = 0
    multiplier: int = 1
    space_kind: SpaceKind | None = None


class Deck:
    """A shuffled deck. Drawn cards go to the bottom unless a player keeps them."""

    def __init__(self, cards: tuple[Card, ...], rng: np.random.Generator) -> None:
        """Shuffle ``cards`` into a new deck using ``rng``."""
        self.size = len(cards)
        self._cards = deque(cards[i] for i in rng.permutation(len(cards)))

    def __len__(self) -> int:
        """Return the number of cards currently in the deck."""
        return len(self._cards)

    def draw(self) -> Card:
        """Take the top card. Brig passes leave the deck until returned."""
        card = self._cards.popleft()
        if card.effect != CardEffect.BRIG_PASS:
            self._cards.append(card)
        return card

    def put_back(self, card: Card) -> None:
        """Return a held card to the bottom of the deck."""
        self._cards.append(card)


def load_cards(path: Path = DATA_DIR / "cards.json") -> dict[str, tuple[Card, ...]]:
    """Load every deck from a JSON file, keyed by deck name."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        deck: tuple(
            Card(
                **{
                    **entry,
                    "deck": deck,
                    "effect": CardEffect(entry["effect"]),
                    "space_kind": SpaceKind(entry["space_kind"])
                    if "space_kind" in entry
                    else None,
                }
            )
            for entry in entries
        )
        for deck, entries in raw.items()
    }


@cache
def default_cards() -> dict[str, tuple[Card, ...]]:
    """Return the shared standard card set."""
    return load_cards()
