"""Rollout worker processes. This module avoids PyTorch so workers start fast."""

from dataclasses import dataclass, field
from multiprocessing.connection import Connection

import numpy as np

from saltmarket.bots.base import Strategy
from saltmarket.bots.catalog import make_bot
from saltmarket.rl import encoding as enc
from saltmarket.rl.agent import AgentStrategy
from saltmarket.rl.env import SaltmarketEnv
from saltmarket.rl.policy import NumpyPolicy, PolicyWeights
from saltmarket.rl.rollout import RolloutCollector

OPPONENT_COUNTS = (1, 3)


@dataclass(slots=True)
class TableSpec:
    """What opponents the current curriculum stage uses."""

    pool: list[str] = field(default_factory=lambda: ["random"])
    snapshots: list[PolicyWeights] = field(default_factory=list)
    snapshot_share: float = 0.0


@dataclass(frozen=True, slots=True)
class RolloutRequest:
    """One round of work for a worker."""

    weights: PolicyWeights
    spec: TableSpec
    steps: int
    gamma: float
    gae_lambda: float


def snapshot_bot(weights: PolicyWeights, rng: np.random.Generator) -> AgentStrategy:
    """Return an opponent that plays a frozen earlier version of the agent."""
    policy = NumpyPolicy(weights)
    return AgentStrategy(lambda obs, mask: policy.sample(obs, mask, rng)[0])


def sample_opponents(spec: TableSpec, rng: np.random.Generator) -> list[Strategy]:
    """Draw a 2-player or 4-player table from the stage's opponents."""
    opponents: list[Strategy] = []
    for _ in range(int(rng.choice(OPPONENT_COUNTS))):
        if spec.snapshots and rng.random() < spec.snapshot_share:
            weights = spec.snapshots[int(rng.integers(len(spec.snapshots)))]
            opponents.append(snapshot_bot(weights, rng))
        else:
            opponents.append(make_bot(spec.pool[int(rng.integers(len(spec.pool)))]))
    return opponents


def worker_main(connection: Connection, seed: int, shaping: float, gamma: float) -> None:
    """Serve rollout requests until told to stop."""
    current = TableSpec()
    env = SaltmarketEnv(
        lambda rng: sample_opponents(current, rng), seed=seed, shaping=shaping, gamma=gamma
    )
    collector = RolloutCollector(env, seed=seed, num_actions=enc.NUM_ACTIONS)
    while (request := connection.recv()) is not None:
        current.pool = request.spec.pool
        current.snapshots = request.spec.snapshots
        current.snapshot_share = request.spec.snapshot_share
        rollout = collector.collect(
            NumpyPolicy(request.weights), request.steps, request.gamma, request.gae_lambda
        )
        connection.send(rollout)
    env.close()
