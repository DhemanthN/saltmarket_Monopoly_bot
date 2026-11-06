"""Collect experience from an environment with the current policy."""

from dataclasses import dataclass, field

import gymnasium as gym
import numpy as np

from saltmarket.rl.advantage import Batch, compute_gae
from saltmarket.rl.policy import NumpyPolicy


@dataclass(slots=True)
class Rollout:
    """Experience from one collector, plus stats on each game that finished."""

    batch: Batch
    episode_returns: list[float] = field(default_factory=list)
    episode_infos: list[dict] = field(default_factory=list)


class RolloutCollector:
    """Steps one env, carrying unfinished episodes across calls."""

    def __init__(self, env: gym.Env, seed: int, num_actions: int) -> None:
        """Reset the env and prepare to collect."""
        self.env = env
        self.num_actions = num_actions
        self.rng = np.random.default_rng(seed)
        self.obs, info = env.reset(seed=seed)
        self.mask = self._mask_from(info)
        self.episode_return = 0.0

    def _mask_from(self, info: dict) -> np.ndarray:
        return info.get("action_mask", np.ones(self.num_actions, dtype=bool))

    def collect(
        self, policy: NumpyPolicy, steps: int, gamma: float, gae_lambda: float
    ) -> Rollout:
        """Run ``steps`` decisions and return the experience."""
        obs = np.zeros((steps, *self.obs.shape), dtype=np.float32)
        masks = np.zeros((steps, self.num_actions), dtype=bool)
        actions = np.zeros(steps, dtype=np.int64)
        log_probs = np.zeros(steps, dtype=np.float32)
        values = np.zeros(steps, dtype=np.float32)
        rewards = np.zeros(steps, dtype=np.float32)
        dones = np.zeros(steps, dtype=bool)
        returns: list[float] = []
        infos: list[dict] = []
        for t in range(steps):
            obs[t], masks[t] = self.obs, self.mask
            actions[t], log_probs[t], values[t] = policy.sample(self.obs, self.mask, self.rng)
            next_obs, reward, terminated, truncated, info = self.env.step(int(actions[t]))
            rewards[t] = reward
            dones[t] = terminated or truncated
            self.episode_return += float(reward)
            if truncated and not terminated:
                rewards[t] += gamma * policy.value(next_obs)
            if dones[t]:
                returns.append(self.episode_return)
                infos.append({k: v for k, v in info.items() if k != "action_mask"})
                self.episode_return = 0.0
                next_obs, info = self.env.reset()
            self.obs, self.mask = next_obs, self._mask_from(info)
        last_value = policy.value(self.obs)
        advantages, targets = compute_gae(rewards, values, dones, last_value, gamma, gae_lambda)
        batch = Batch(obs, masks, actions, log_probs, advantages, targets)
        return Rollout(batch, returns, infos)


def merge_batches(batches: list[Batch]) -> Batch:
    """Join batches from several collectors."""
    return Batch(
        *(
            np.concatenate([getattr(batch, name) for batch in batches])
            for name in ("obs", "masks", "actions", "log_probs", "advantages", "returns")
        )
    )
