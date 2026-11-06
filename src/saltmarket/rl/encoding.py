"""The agent's fixed action list and numeric observation vector. See docs/rl.md."""

from dataclasses import dataclass
from enum import IntEnum

import numpy as np

from saltmarket.engine import rules
from saltmarket.engine.board import default_board
from saltmarket.engine.rules import PORT_LEVEL
from saltmarket.engine.state import GameState
from saltmarket.engine.trade import TradeOffer

BOARD = default_board()
GROUPS = tuple(BOARD.groups)
OWNABLE = BOARD.ownable
OWNABLE_SLOT = {index: slot for slot, index in enumerate(OWNABLE)}
MAX_PLAYERS = 4

BID_LEVELS = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0)
TRADE_PREMIUMS = (1.0, 1.5, 2.0)

PASS = 0
YES = 1
BID = 2
BUILD = BID + len(BID_LEVELS)
SELL = BUILD + len(GROUPS)
MORTGAGE = SELL + len(GROUPS)
UNMORTGAGE = MORTGAGE + len(OWNABLE)
BRIG_ROLL = UNMORTGAGE + len(OWNABLE)
BRIG_PAY = BRIG_ROLL + 1
BRIG_PASS = BRIG_ROLL + 2
TRADE = BRIG_ROLL + 3
NUM_ACTIONS = TRADE + len(GROUPS) * len(TRADE_PREMIUMS)

CASH_SCALE = 3000.0
WORTH_SCALE = 10000.0
PRICE_SCALE = 400.0
AMOUNT_SCALE = 1000.0


class DecisionKind(IntEnum):
    """The kinds of decision the agent is asked to make."""

    BUY = 0
    AUCTION = 1
    BUILD = 2
    LIQUIDATE = 3
    UNMORTGAGE = 4
    BRIG = 5
    PROPOSE = 6
    ACCEPT = 7
    RAISE_CASH = 8


@dataclass(frozen=True, slots=True)
class Context:
    """Details of the current decision."""

    space: int | None = None
    amount: int = 0
    offer: TradeOffer | None = None


PER_SPACE = MAX_PLAYERS + 2
PER_PLAYER = 6
PER_GROUP = 3
TRADE_FEATURES = 6
GLOBAL_FEATURES = 5
OBS_SIZE = (
    PER_SPACE * len(OWNABLE)
    + PER_PLAYER * MAX_PLAYERS
    + PER_GROUP * len(GROUPS)
    + len(DecisionKind)
    + len(OWNABLE)
    + 2
    + TRADE_FEATURES
    + GLOBAL_FEATURES
)


def _trade_features(state: GameState, me: int, offer: TradeOffer) -> list[float]:
    def worth(spaces: tuple[int, ...]) -> float:
        return sum(state.board[i].price for i in spaces) / AMOUNT_SCALE

    def completes(player: int, spaces: tuple[int, ...]) -> float:
        for index in spaces:
            group = state.board[index].group
            lots = state.board.groups[group] if group else ()
            if lots and all(state.owner[i] == player or i in spaces for i in lots):
                return 1.0
        return 0.0

    return [
        offer.give_cash / AMOUNT_SCALE,
        offer.take_cash / AMOUNT_SCALE,
        worth(offer.give_spaces),
        worth(offer.take_spaces),
        completes(me, offer.give_spaces),
        completes(offer.proposer, offer.take_spaces),
    ]


def encode(state: GameState, me: int, kind: DecisionKind, context: Context) -> np.ndarray:
    """Return the observation for a decision, with seats relative to the agent."""
    count = len(state.players)
    obs = np.zeros(OBS_SIZE, dtype=np.float32)
    position = 0
    for index in OWNABLE:
        owner = state.owner[index]
        if owner is not None:
            obs[position + (owner - me) % count] = 1.0
        obs[position + MAX_PLAYERS] = state.level[index] / PORT_LEVEL
        obs[position + MAX_PLAYERS + 1] = state.mortgaged[index]
        position += PER_SPACE

    for offset in range(count):
        player = state.players[(me + offset) % count]
        start = position + offset * PER_PLAYER
        obs[start] = player.cash / CASH_SCALE
        obs[start + 1] = player.position / state.board.size
        obs[start + 2] = player.in_brig
        obs[start + 3] = len(player.passes) / 2
        obs[start + 4] = not player.bankrupt
        obs[start + 5] = rules.net_worth(state, player.id) / WORTH_SCALE
    position += PER_PLAYER * MAX_PLAYERS

    for group in GROUPS:
        lots = state.board.groups[group]
        owners = [state.owner[i] for i in lots]
        obs[position] = owners.count(me) / len(lots)
        single = owners[0] if len(set(owners)) == 1 else None
        obs[position + 1] = single == me
        obs[position + 2] = single is not None and single != me
        position += PER_GROUP

    obs[position + kind] = 1.0
    position += len(DecisionKind)
    if context.space is not None:
        obs[position + OWNABLE_SLOT[context.space]] = 1.0
    position += len(OWNABLE)
    if context.space is not None:
        obs[position] = state.board[context.space].price / PRICE_SCALE
    obs[position + 1] = context.amount / AMOUNT_SCALE
    position += 2
    if context.offer is not None:
        obs[position : position + TRADE_FEATURES] = _trade_features(state, me, context.offer)
    position += TRADE_FEATURES

    ownable = len(OWNABLE)
    obs[position] = sum(state.owner[i] is None for i in OWNABLE) / ownable
    obs[position + 1] = state.turn / state.config.turn_cap
    obs[position + 2] = state.depots_left / max(1, state.config.total_depots)
    obs[position + 3] = state.ports_left / max(1, state.config.total_ports)
    obs[position + 4] = count / MAX_PLAYERS
    return obs
