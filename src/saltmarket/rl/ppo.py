"""Proximal Policy Optimization, written directly in PyTorch.

PPO improves a policy from batches of its own experience. The clipped objective stops any
one update from moving the policy too far from the one that collected the data.
"""

from dataclasses import dataclass

import numpy as np
import torch
from torch import nn

from saltmarket.rl.advantage import Batch, compute_gae
from saltmarket.rl.policy import MASKED_LOGIT, PolicyWeights

__all__ = ["PPO", "ActorCritic", "Batch", "PPOConfig", "compute_gae"]


@dataclass(frozen=True, slots=True)
class PPOConfig:
    """PPO hyperparameters."""

    learning_rate: float = 3e-4
    gamma: float = 0.999
    gae_lambda: float = 0.95
    clip_range: float = 0.2
    entropy_coef: float = 0.01
    value_coef: float = 0.5
    epochs: int = 4
    minibatch_size: int = 4096
    max_grad_norm: float = 0.5
    hidden_size: int = 256


def _mlp(sizes: tuple[int, ...], final_gain: float) -> nn.Sequential:
    layers: list[nn.Module] = []
    for position, (inputs, outputs) in enumerate(zip(sizes, sizes[1:], strict=False)):
        linear = nn.Linear(inputs, outputs)
        last = position == len(sizes) - 2
        nn.init.orthogonal_(linear.weight, final_gain if last else 2**0.5)
        nn.init.zeros_(linear.bias)
        layers.append(linear)
        if not last:
            layers.append(nn.Tanh())
    return nn.Sequential(*layers)


class ActorCritic(nn.Module):
    """Separate networks: the actor picks actions and the critic predicts outcomes."""

    def __init__(self, obs_size: int, num_actions: int, hidden: int) -> None:
        """Build both networks with orthogonal initialization."""
        super().__init__()
        self.actor = _mlp((obs_size, hidden, hidden, num_actions), 0.01)
        self.critic = _mlp((obs_size, hidden, hidden, 1), 1.0)

    def evaluate(
        self, obs: torch.Tensor, masks: torch.Tensor, actions: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Return log probabilities, entropy, and values under the masked policy."""
        logits = self.actor(obs).masked_fill(~masks, MASKED_LOGIT)
        distribution = torch.distributions.Categorical(logits=logits)
        return (
            distribution.log_prob(actions),
            distribution.entropy(),
            self.critic(obs).squeeze(-1),
        )

    def numpy_weights(self) -> PolicyWeights:
        """Export the weights for ``NumpyPolicy``."""
        def export(network: nn.Sequential) -> tuple:
            return tuple(
                (
                    layer.weight.detach().cpu().numpy().T.copy(),
                    layer.bias.detach().cpu().numpy().copy(),
                )
                for layer in network
                if isinstance(layer, nn.Linear)
            )

        return PolicyWeights(export(self.actor), export(self.critic))


class PPO:
    """Holds the network and optimizer, and applies updates."""

    def __init__(
        self,
        obs_size: int,
        num_actions: int,
        config: PPOConfig,
        device: str = "cpu",
        seed: int = 0,
    ) -> None:
        """Create a new seeded network and optimizer."""
        torch.manual_seed(seed)
        self.config = config
        self.device = torch.device(device)
        self.model = ActorCritic(obs_size, num_actions, config.hidden_size).to(self.device)
        self.optimizer = torch.optim.Adam(
            self.model.parameters(), lr=config.learning_rate, eps=1e-5
        )
        self.generator = np.random.default_rng(seed)

    def update(self, batch: Batch) -> dict[str, float]:
        """Run several epochs of clipped updates. Return average diagnostics."""
        config = self.config

        def tensor(array: np.ndarray, dtype: torch.dtype) -> torch.Tensor:
            return torch.as_tensor(array, dtype=dtype, device=self.device)

        obs = tensor(batch.obs, torch.float32)
        masks = tensor(batch.masks, torch.bool)
        actions = tensor(batch.actions, torch.long)
        old_log_probs = tensor(batch.log_probs, torch.float32)
        advantages = tensor(batch.advantages, torch.float32)
        returns = tensor(batch.returns, torch.float32)

        size = len(batch.actions)
        totals = {"policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0, "clip_fraction": 0.0}
        updates = 0
        for _ in range(config.epochs):
            order = self.generator.permutation(size)
            for start in range(0, size, config.minibatch_size):
                rows = torch.as_tensor(
                    order[start : start + config.minibatch_size], device=self.device
                )
                log_probs, entropy, values = self.model.evaluate(
                    obs[rows], masks[rows], actions[rows]
                )
                chunk = advantages[rows]
                chunk = (chunk - chunk.mean()) / (chunk.std() + 1e-8)
                ratio = (log_probs - old_log_probs[rows]).exp()
                clipped = ratio.clamp(1 - config.clip_range, 1 + config.clip_range)
                policy_loss = -torch.min(ratio * chunk, clipped * chunk).mean()
                value_loss = (values - returns[rows]).pow(2).mean()
                entropy_mean = entropy.mean()
                loss = (
                    policy_loss
                    + config.value_coef * value_loss
                    - config.entropy_coef * entropy_mean
                )
                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.model.parameters(), config.max_grad_norm)
                self.optimizer.step()
                totals["policy_loss"] += policy_loss.item()
                totals["value_loss"] += value_loss.item()
                totals["entropy"] += entropy_mean.item()
                outside = (ratio - 1).abs() > config.clip_range
                totals["clip_fraction"] += outside.float().mean().item()
                updates += 1
        return {name: total / updates for name, total in totals.items()}
