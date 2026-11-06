"""Choices a strategy can hand back to the game loop."""

from dataclasses import dataclass
from enum import StrEnum


class BrigChoice(StrEnum):
    """How a player tries to leave the Brig at the start of their turn."""

    ROLL = "roll"
    PAY = "pay"
    USE_PASS = "use_pass"


class LiquidationKind(StrEnum):
    """Ways to turn assets into cash."""

    SELL_BUILDING = "sell_building"
    SELL_GROUP = "sell_group"
    MORTGAGE = "mortgage"


@dataclass(frozen=True, slots=True)
class Liquidation:
    """Raise cash from the space at ``index``, or from its whole group for SELL_GROUP."""

    kind: LiquidationKind
    index: int
