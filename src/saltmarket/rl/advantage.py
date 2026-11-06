"""Experience batches and advantage estimates, kept free of PyTorch for fast workers."""

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class Batch:
    """Flat arrays of experience, with advantages and returns already computed."""

    obs: np.ndarray
    masks: np.ndarray
    actions: np.ndarray
    log_probs: np.ndarray
    advantages: np.ndarray
    returns: np.ndarray


def compute_gae(
    rewards: np.ndarray,
    values: np.ndarray,
    dones: np.ndarray,
    last_value: float,
    gamma: float,
    lam: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Return generalized advantage estimates and value targets.

    An advantage says how much better an action turned out than the critic expected.
    ``lam`` blends short-horizon estimates (low variance) with long ones (low bias).
    """
    advantages = np.zeros_like(rewards, dtype=np.float32)
    running = 0.0
    next_value = last_value
    for t in range(len(rewards) - 1, -1, -1):
        alive = 1.0 - float(dones[t])
        delta = rewards[t] + gamma * next_value * alive - values[t]
        running = delta + gamma * lam * alive * running
        advantages[t] = running
        next_value = values[t]
    return advantages, advantages + values
