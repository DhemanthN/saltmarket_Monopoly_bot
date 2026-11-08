"""Experience collection for DQN. Like ``workers``, this module avoids PyTorch."""

from collections import deque
from dataclasses import dataclass, field
from functools import partial
from multiprocessing.connection import Connection

import gymnasium as gym
import numpy as np

from saltmarket.rl import encoding as enc
from saltmarket.rl.agent import AgentStrategy
from saltmarket.rl.env import SaltmarketEnv
from saltmarket.rl.policy import NumpyPolicy, PolicyWeights
from saltmarket.rl.workers import TableSpec, sample_opponents

SNAPSHOT_EPSILON = 0.05


@dataclass(slots=True)
class Transitions:
    """Flat arrays of n-step transitions.

    ``rewards`` already holds the discounted reward over up to ``n_step`` decisions, and
    ``discounts`` holds gamma to the power of the decisions actually covered. A discount
    of 0 marks a game that ended, so its next state is never bootstrapped.
    """

    obs: np.ndarray
    masks: np.ndarray
    actions: np.ndarray
    rewards: np.ndarray
    discounts: np.ndarray
    next_obs: np.ndarray
    next_masks: np.ndarray

    def __len__(self) -> int:
        """Return the number of transitions."""
        return len(self.actions)


FIELDS = ("obs", "masks", "actions", "rewards", "discounts", "next_obs", "next_masks")


def merge_transitions(parts: list[Transitions]) -> Transitions:
    """Join transitions from several collectors."""
    return Transitions(
        *(np.concatenate([getattr(part, name) for part in parts]) for name in FIELDS)
    )


@dataclass(slots=True)
class Experience:
    """Transitions from one collector, plus stats on each game that finished."""

    transitions: Transitions
    episode_returns: list[float] = field(default_factory=list)
    episode_infos: list[dict] = field(default_factory=list)


def epsilon_greedy(
    policy: NumpyPolicy,
    obs: np.ndarray,
    mask: np.ndarray,
    epsilon: float,
    rng: np.random.Generator,
) -> int:
    """With chance ``epsilon`` pick a random legal action, otherwise the best one."""
    if rng.random() < epsilon:
        legal = np.flatnonzero(mask)
        return int(legal[rng.integers(len(legal))])
    return policy.greedy(obs, mask)


def q_snapshot_bot(weights: PolicyWeights, rng: np.random.Generator) -> AgentStrategy:
    """Return an opponent that plays a frozen earlier Q-network, with a little noise."""
    policy = NumpyPolicy(weights)
    return AgentStrategy(partial(_snapshot_move, policy, rng))


def _snapshot_move(
    policy: NumpyPolicy, rng: np.random.Generator, obs: np.ndarray, mask: np.ndarray
) -> int:
    return epsilon_greedy(policy, obs, mask, SNAPSHOT_EPSILON, rng)


class TransitionCollector:
    """Steps one env with an epsilon-greedy policy and builds n-step transitions.

    Unfinished games carry over between calls, so a call may return slightly more or
    fewer transitions than the decisions it ran.
    """

    def __init__(
        self, env: gym.Env, seed: int, num_actions: int, gamma: float, n_step: int
    ) -> None:
        """Reset the env and prepare to collect."""
        self.env = env
        self.num_actions = num_actions
        self.gamma = gamma
        self.n_step = n_step
        self.rng = np.random.default_rng(seed)
        self.obs, info = env.reset(seed=seed)
        self.mask = self._mask_from(info)
        self.pending: deque[tuple[np.ndarray, np.ndarray, int, float]] = deque()
        self.episode_return = 0.0

    def _mask_from(self, info: dict) -> np.ndarray:
        return info.get("action_mask", np.ones(self.num_actions, dtype=bool))

    def _emit(
        self, out: list[tuple], next_obs: np.ndarray, next_mask: np.ndarray, ended: bool
    ) -> None:
        """Turn the oldest pending decision into a transition."""
        rewards = [step[3] for step in self.pending]
        discounted = sum(reward * self.gamma**i for i, reward in enumerate(rewards))
        discount = 0.0 if ended else self.gamma ** len(rewards)
        obs, mask, action, _ = self.pending.popleft()
        out.append((obs, mask, action, discounted, discount, next_obs, next_mask))

    def collect(self, policy: NumpyPolicy, steps: int, epsilon: float) -> Experience:
        """Run ``steps`` decisions and return the finished transitions."""
        out: list[tuple] = []
        returns: list[float] = []
        infos: list[dict] = []
        for _ in range(steps):
            action = epsilon_greedy(policy, self.obs, self.mask, epsilon, self.rng)
            next_obs, reward, terminated, truncated, info = self.env.step(action)
            self.pending.append((self.obs, self.mask, action, float(reward)))
            self.episode_return += float(reward)
            next_mask = self._mask_from(info)
            if terminated:
                next_mask = np.zeros(self.num_actions, dtype=bool)
            if len(self.pending) == self.n_step:
                self._emit(out, next_obs, next_mask, terminated)
            if terminated or truncated:
                while self.pending:
                    self._emit(out, next_obs, next_mask, terminated)
                returns.append(self.episode_return)
                infos.append({k: v for k, v in info.items() if k != "action_mask"})
                self.episode_return = 0.0
                next_obs, info = self.env.reset()
                next_mask = self._mask_from(info)
            self.obs, self.mask = next_obs, next_mask
        return Experience(self._stack(out), returns, infos)

    def _stack(self, rows: list[tuple]) -> Transitions:
        if not rows:
            size = self.obs.shape[0]
            return Transitions(
                np.zeros((0, size), np.float32), np.zeros((0, self.num_actions), bool),
                np.zeros(0, np.int64), np.zeros(0, np.float32), np.zeros(0, np.float32),
                np.zeros((0, size), np.float32), np.zeros((0, self.num_actions), bool),
            )
        columns = list(zip(*rows, strict=True))
        types = (np.float32, bool, np.int64, np.float32, np.float32, np.float32, bool)
        return Transitions(
            *(np.asarray(column, dtype=kind) for column, kind in zip(columns, types, strict=True))
        )


@dataclass(frozen=True, slots=True)
class DQNRequest:
    """One round of collection for a worker."""

    weights: PolicyWeights
    spec: TableSpec
    steps: int
    epsilon: float


def dqn_worker_main(
    connection: Connection, seed: int, shaping: float, gamma: float, n_step: int
) -> None:
    """Serve collection requests until told to stop."""
    current = TableSpec()
    env = SaltmarketEnv(
        lambda rng: sample_opponents(current, rng, q_snapshot_bot),
        seed=seed,
        shaping=shaping,
        gamma=gamma,
    )
    collector = TransitionCollector(env, seed, enc.NUM_ACTIONS, gamma, n_step)
    while (request := connection.recv()) is not None:
        current.pool = request.spec.pool
        current.snapshots = request.spec.snapshots
        current.snapshot_share = request.spec.snapshot_share
        current.opponent_counts = request.spec.opponent_counts
        experience = collector.collect(NumpyPolicy(request.weights), request.steps, request.epsilon)
        connection.send(experience)
    env.close()
