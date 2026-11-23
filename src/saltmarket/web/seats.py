"""Seats a person or a trained agent can fill. Both reuse the agent's masked action list."""

from collections.abc import Callable
from functools import cache
from pathlib import Path
from typing import Protocol

import numpy as np

from saltmarket.bots.base import Strategy
from saltmarket.bots.registry import ALL_NAMED_BOTS, make_any_bot
from saltmarket.engine.state import GameState, IllegalMoveError
from saltmarket.rl import encoding as enc
from saltmarket.rl.agent import AgentStrategy
from saltmarket.rl.encoding import Context, DecisionKind
from saltmarket.rl.policy import NumpyPolicy, load_policy
from saltmarket.web.contract import (
    ActionId,
    AgentName,
    Decision,
    ExplainedAction,
    Explanation,
    LegalAction,
)
from saltmarket.web.labels import legal_actions, offer_view

HUMAN = "human"
AGENTS = ("ppo", "dqn")
TOP_ACTIONS = 3
DQN_MODEL = "dqn_two_player"


class Observer(Protocol):
    """Receives a record of every decision a seat makes."""

    def record_decision(
        self, seat: int, kind: DecisionKind, action: ActionId, explanation: Explanation | None
    ) -> None:
        """Log that ``seat`` chose ``action``."""


class AwaitingHuman(Exception):
    """Raised to stop the game at a decision the human has not answered yet."""

    def __init__(self, decision: Decision) -> None:
        """Keep the decision so the session can show it."""
        super().__init__(decision.kind)
        self.decision = decision


def _never_decides(obs: np.ndarray, mask: np.ndarray) -> int:
    raise NotImplementedError("Seats answer through _ask, not decide")


class _Seat(AgentStrategy):
    """Shared parts of the human and agent seats."""

    def __init__(self, decide: Callable[[np.ndarray, np.ndarray], int]) -> None:
        """Start with no observer. The game sets one to log decisions."""
        super().__init__(decide)
        self.observer: Observer | None = None

    def _legal(
        self, state: GameState, kind: DecisionKind, mask: np.ndarray, context: Context
    ) -> tuple[LegalAction, ...]:
        trades = self._trade_options(state) if kind == DecisionKind.PROPOSE else {}
        return legal_actions(state, self.me, kind, mask, context, trades)

    def _announce(
        self, kind: DecisionKind, action: ActionId, explanation: Explanation | None = None
    ) -> None:
        if self.observer is not None:
            self.observer.record_decision(self.me, kind, action, explanation)


class HumanSeat(_Seat):
    """A person. Each decision goes to ``answer``, which returns one of the legal ids.

    Only masked-legal actions are offered. An answer outside them raises
    ``IllegalMoveError`` instead of being passed to the engine.
    """

    name = HUMAN

    def __init__(self, answer: Callable[[Decision], ActionId]) -> None:
        """Store the function that supplies the person's choices."""
        super().__init__(_never_decides)
        self.answer = answer

    def _ask(
        self, state: GameState, kind: DecisionKind, mask: np.ndarray, context: Context
    ) -> int:
        priced = kind in (DecisionKind.BUY, DecisionKind.AUCTION)
        decision = Decision(
            kind=kind.name.lower(),
            seat=self.me,
            turn=state.turn,
            legal=self._legal(state, kind, mask, context),
            space=context.space,
            price=state.board[context.space].price if priced else None,
            debt=context.amount if kind == DecisionKind.RAISE_CASH else None,
            offer=offer_view(context.offer) if context.offer else None,
        )
        action = self.answer(decision)
        if not 0 <= action < enc.NUM_ACTIONS or not mask[action]:
            raise IllegalMoveError(f"Action {action} is not legal for {decision.kind}")
        self._announce(kind, action)
        return action


class AgentSeat(_Seat):
    """A trained agent that plays its best legal action and explains each move."""

    def __init__(self, agent: AgentName, policy: NumpyPolicy, model: str) -> None:
        """Wrap a policy. ``model`` names the weights file, so the site can say what played."""
        super().__init__(policy.greedy)
        self.agent = agent
        self.policy = policy
        self.model = model
        self.name = agent

    def _scores(self, obs: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, float]:
        """Return a score per action and the critic's value.

        PPO scores are probabilities. DQN scores are Q-values, rebuilt with the dueling
        formula Q = V + A - mean of A over legal actions (see ``DuelingQNetwork``).
        """
        value = self.policy.value(obs)
        if self.agent == "ppo":
            return self.policy.probabilities(obs, mask), value
        advantages = self.policy.advantages(obs)
        return value + advantages - advantages[mask].mean(), value

    def _explain(
        self, obs: np.ndarray, mask: np.ndarray, legal: tuple[LegalAction, ...]
    ) -> Explanation:
        scores, value = self._scores(obs, mask)
        ranked = sorted(legal, key=lambda action: -scores[action.id])[:TOP_ACTIONS]
        is_ppo = self.agent == "ppo"
        top = tuple(
            ExplainedAction(
                a.id,
                a.label,
                prob=round(float(scores[a.id]), 4) if is_ppo else None,
                q=None if is_ppo else round(float(scores[a.id]), 3),
            )
            for a in ranked
        )
        return Explanation(self.agent, self.model, top, round(value, 3))

    def _ask(
        self, state: GameState, kind: DecisionKind, mask: np.ndarray, context: Context
    ) -> int:
        obs = enc.encode(state, self.me, kind, context)
        action = self.decide(obs, mask)
        legal = self._legal(state, kind, mask, context)
        self._announce(kind, action, self._explain(obs, mask, legal))
        return action


def agent_model(agent: AgentName, num_seats: int) -> str:
    """Return the weights file to use. PPO has a 2-player and a 4-player model, DQN only 2."""
    if agent == "dqn":
        return DQN_MODEL
    return "two_player" if num_seats == 2 else "main"


@cache
def _load_policy(path: Path) -> NumpyPolicy:
    return NumpyPolicy(load_policy(path))


def make_seat(
    kind: str,
    num_seats: int,
    answer: Callable[[Decision], ActionId],
    models_dir: Path,
) -> Strategy:
    """Build the strategy for a seat: ``human``, ``ppo``, ``dqn``, or a bot name."""
    if kind == HUMAN:
        return HumanSeat(answer)
    if kind in AGENTS:
        model = agent_model(kind, num_seats)
        return AgentSeat(kind, _load_policy(models_dir / f"{model}.npz"), model)
    if kind not in ALL_NAMED_BOTS:
        raise ValueError(f"Unknown seat {kind!r}")
    return make_any_bot(kind)
