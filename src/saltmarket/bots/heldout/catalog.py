"""The held-out bots. None of them is used in any training stage.

See the "Held-out bots" section of docs/strategies.md for what each one tries to do.
"""

from saltmarket.bots.base import Strategy
from saltmarket.bots.heldout.adaptive import Finisher, PhaseShifter, ScoreAware
from saltmarket.bots.heldout.exploits import LeveragedBuyer, StalemateSeeker
from saltmarket.bots.heldout.markov_aware import AmbushBuilder, NpvBidder, RiskManager
from saltmarket.bots.heldout.opponents import (
    CashReader,
    LeaderDenier,
    Reciprocator,
    RivalWatcher,
)
from saltmarket.bots.heldout.trading import MortgageFlipper, SwapNegotiator

ALL_HELDOUT_BOTS: tuple[type[Strategy], ...] = (
    PhaseShifter, ScoreAware, Finisher, RivalWatcher, LeaderDenier, CashReader,
    Reciprocator, SwapNegotiator, MortgageFlipper, RiskManager, AmbushBuilder, NpvBidder,
    StalemateSeeker, LeveragedBuyer,
)
HELDOUT_BOTS: dict[str, type[Strategy]] = {bot.name: bot for bot in ALL_HELDOUT_BOTS}
