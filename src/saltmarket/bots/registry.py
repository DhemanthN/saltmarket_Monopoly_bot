"""Lookup across both bot catalogs.

Training and the tournament use only ``catalog.BOTS``. Evaluation and fuzz testing
use this module so they can also build the held-out bots by name.
"""

from saltmarket.bots.base import Strategy
from saltmarket.bots.catalog import BOTS
from saltmarket.bots.heldout.catalog import HELDOUT_BOTS

TRAINING_BOTS = BOTS
ALL_NAMED_BOTS: dict[str, type[Strategy]] = {**BOTS, **HELDOUT_BOTS}


def make_any_bot(name: str) -> Strategy:
    """Create a new training or held-out bot by name."""
    return ALL_NAMED_BOTS[name]()
