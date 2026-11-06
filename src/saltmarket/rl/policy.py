"""NumPy copy of the trained network, for fast single-step play without PyTorch."""

from dataclasses import dataclass

import numpy as np

MASKED_LOGIT = -1e9


@dataclass(frozen=True, slots=True)
class PolicyWeights:
    """Weight and bias pairs for the actor and critic, in layer order."""

    actor: tuple[tuple[np.ndarray, np.ndarray], ...]
    critic: tuple[tuple[np.ndarray, np.ndarray], ...]


def _forward(layers: tuple[tuple[np.ndarray, np.ndarray], ...], x: np.ndarray) -> np.ndarray:
    for weight, bias in layers[:-1]:
        x = np.tanh(x @ weight + bias)
    weight, bias = layers[-1]
    return x @ weight + bias


class NumpyPolicy:
    """Chooses masked actions and estimates values."""

    def __init__(self, weights: PolicyWeights) -> None:
        """Wrap a set of network weights."""
        self.weights = weights

    def value(self, obs: np.ndarray) -> float:
        """Return the critic's estimate for an observation."""
        return float(_forward(self.weights.critic, obs)[0])

    def _log_probs(self, obs: np.ndarray, mask: np.ndarray) -> np.ndarray:
        logits = np.where(mask, _forward(self.weights.actor, obs), MASKED_LOGIT)
        logits = logits - logits.max()
        return logits - np.log(np.exp(logits).sum())

    def sample(
        self, obs: np.ndarray, mask: np.ndarray, rng: np.random.Generator
    ) -> tuple[int, float, float]:
        """Sample an action. Return the action, its log probability, and the value."""
        log_probs = self._log_probs(obs, mask)
        probs = np.exp(log_probs)
        action = int(np.searchsorted(np.cumsum(probs), rng.random() * probs.sum()))
        action = min(action, len(probs) - 1)
        if not mask[action]:
            action = int(np.flatnonzero(mask)[-1])
        return action, float(log_probs[action]), self.value(obs)

    def greedy(self, obs: np.ndarray, mask: np.ndarray) -> int:
        """Return the most likely legal action."""
        return int(np.argmax(self._log_probs(obs, mask)))
