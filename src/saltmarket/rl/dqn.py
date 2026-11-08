"""Double DQN with a dueling network, experience replay, and a target network.

DQN learns Q(s, a): how much reward to expect after taking action ``a`` in state ``s``
and playing well afterwards. The agent then picks the action with the highest Q-value.

- **Dueling heads:** the network splits Q into a state value V(s) and an advantage
  A(s, a) for each action, so it can learn how good a position is without having to
  learn it separately for every action.
- **Experience replay:** past transitions are stored and sampled at random, which breaks
  the correlation between consecutive decisions in one game.
- **Target network:** a lagged copy of the network computes learning targets, so the
  targets do not shift with every gradient step.
- **Double DQN:** the online network chooses the next action and the target network
  scores it, which reduces the overestimation that a plain max causes.

Illegal actions get a Q-value of minus infinity, both when acting and inside the target
max, so the agent never chooses them and never learns from their values.
"""

from dataclasses import dataclass

import numpy as np
import torch
from torch import nn
from torch.nn import functional

from saltmarket.rl.dqn_workers import FIELDS, Transitions, merge_transitions
from saltmarket.rl.policy import PolicyWeights

__all__ = [
    "DQN",
    "DQNConfig",
    "DuelingQNetwork",
    "ReplayBuffer",
    "Transitions",
    "double_dqn_targets",
    "masked_q_values",
    "merge_transitions",
]


@dataclass(frozen=True, slots=True)
class DQNConfig:
    """DQN hyperparameters."""

    learning_rate: float = 1e-4
    gamma: float = 0.999
    n_step: int = 8
    batch_size: int = 512
    buffer_size: int = 500_000
    target_update_every: int = 250
    max_grad_norm: float = 10.0
    hidden_size: int = 256


class ReplayBuffer:
    """Fixed-size ring buffer of transitions. The oldest are overwritten first."""

    def __init__(self, capacity: int, obs_size: int, num_actions: int) -> None:
        """Allocate storage for ``capacity`` transitions."""
        self.capacity = capacity
        self.obs = np.zeros((capacity, obs_size), dtype=np.float32)
        self.masks = np.zeros((capacity, num_actions), dtype=bool)
        self.actions = np.zeros(capacity, dtype=np.int64)
        self.rewards = np.zeros(capacity, dtype=np.float32)
        self.discounts = np.zeros(capacity, dtype=np.float32)
        self.next_obs = np.zeros((capacity, obs_size), dtype=np.float32)
        self.next_masks = np.zeros((capacity, num_actions), dtype=bool)
        self.position = 0
        self.size = 0

    def __len__(self) -> int:
        """Return how many transitions are stored."""
        return self.size

    def add(self, batch: Transitions) -> None:
        """Store a batch, wrapping around when the buffer is full."""
        count = len(batch)
        if count > self.capacity:
            batch = Transitions(*(getattr(batch, name)[-self.capacity :] for name in FIELDS))
            count = self.capacity
        rows = (self.position + np.arange(count)) % self.capacity
        for name in FIELDS:
            getattr(self, name)[rows] = getattr(batch, name)
        self.position = int((self.position + count) % self.capacity)
        self.size = min(self.size + count, self.capacity)

    def sample(self, batch_size: int, rng: np.random.Generator) -> Transitions:
        """Draw ``batch_size`` stored transitions uniformly, with replacement."""
        if self.size == 0:
            raise ValueError("Cannot sample from an empty replay buffer")
        rows = rng.integers(self.size, size=batch_size)
        return Transitions(*(getattr(self, name)[rows] for name in FIELDS))

    def state_dict(self) -> dict[str, np.ndarray]:
        """Return the stored transitions and write position, for checkpoints."""
        arrays = {name: getattr(self, name)[: self.size] for name in FIELDS}
        return {**arrays, "position": np.array(self.position), "size": np.array(self.size)}

    def load_state_dict(self, state: dict[str, np.ndarray]) -> None:
        """Restore transitions saved by ``state_dict``."""
        self.size = int(state["size"])
        self.position = int(state["position"])
        for name in FIELDS:
            getattr(self, name)[: self.size] = state[name]


def _linear(inputs: int, outputs: int, gain: float) -> nn.Linear:
    layer = nn.Linear(inputs, outputs)
    nn.init.orthogonal_(layer.weight, gain)
    nn.init.zeros_(layer.bias)
    return layer


class DuelingQNetwork(nn.Module):
    """A shared trunk followed by a value head and an advantage head.

    Q(s, a) = V(s) + A(s, a) - mean of A over the legal actions. Subtracting the mean
    makes the split unique, and using only legal actions keeps illegal ones from moving
    it. The trunk uses tanh like the PPO networks, so the same NumPy code can run it.
    Both heads start with small weights so every Q-value starts near 0.
    """

    def __init__(self, obs_size: int, num_actions: int, hidden: int) -> None:
        """Build the network with orthogonal initialization."""
        super().__init__()
        self.trunk = nn.Sequential(
            _linear(obs_size, hidden, 2**0.5),
            nn.Tanh(),
            _linear(hidden, hidden, 2**0.5),
            nn.Tanh(),
        )
        self.value = _linear(hidden, 1, 0.01)
        self.advantage = _linear(hidden, num_actions, 0.01)

    def forward(self, obs: torch.Tensor, masks: torch.Tensor) -> torch.Tensor:
        """Return Q-values, with minus infinity for illegal actions."""
        features = self.trunk(obs)
        advantages = self.advantage(features)
        legal = masks.float()
        mean = (advantages * legal).sum(-1, keepdim=True) / legal.sum(-1, keepdim=True).clamp(
            min=1.0
        )
        return masked_q_values(self.value(features) + advantages - mean, masks)

    def numpy_weights(self) -> PolicyWeights:
        """Export for ``NumpyPolicy``.

        The "actor" path is trunk plus advantage head. Within one state V(s) and the mean
        are the same for every action, so the action with the highest advantage is also
        the action with the highest Q-value, and ``NumpyPolicy.greedy`` picks it. The
        "critic" path is trunk plus value head.
        """
        def export(layers: list[nn.Linear]) -> tuple:
            return tuple(
                (
                    layer.weight.detach().cpu().numpy().T.copy(),
                    layer.bias.detach().cpu().numpy().copy(),
                )
                for layer in layers
            )

        trunk = [layer for layer in self.trunk if isinstance(layer, nn.Linear)]
        return PolicyWeights(export([*trunk, self.advantage]), export([*trunk, self.value]))


def masked_q_values(q_values: torch.Tensor, masks: torch.Tensor) -> torch.Tensor:
    """Set the Q-values of illegal actions to minus infinity."""
    return q_values.masked_fill(~masks, float("-inf"))


def double_dqn_targets(
    online_next_q: torch.Tensor,
    target_next_q: torch.Tensor,
    rewards: torch.Tensor,
    discounts: torch.Tensor,
) -> torch.Tensor:
    """Return the Double DQN learning targets.

    Both Q tensors must already be masked, so illegal actions hold minus infinity and
    cannot be chosen by the argmax. The online network picks the best legal next action
    and the target network scores it. Finished games have a discount of 0 and no legal
    next action, so their target is just the reward.
    """
    best = online_next_q.argmax(dim=-1, keepdim=True)
    next_value = target_next_q.gather(-1, best).squeeze(-1)
    bootstrap = torch.where(discounts > 0, discounts * next_value, torch.zeros_like(next_value))
    return rewards + bootstrap


class DQN:
    """Holds the online and target networks and the optimizer, and applies updates."""

    def __init__(
        self,
        obs_size: int,
        num_actions: int,
        config: DQNConfig,
        device: str = "cpu",
        seed: int = 0,
    ) -> None:
        """Create seeded networks, with the target starting as a copy of the online one."""
        torch.manual_seed(seed)
        self.config = config
        self.device = torch.device(device)
        self.online = DuelingQNetwork(obs_size, num_actions, config.hidden_size).to(self.device)
        self.target = DuelingQNetwork(obs_size, num_actions, config.hidden_size).to(self.device)
        self.target.load_state_dict(self.online.state_dict())
        self.target.requires_grad_(False)
        self.optimizer = torch.optim.Adam(
            self.online.parameters(), lr=config.learning_rate, eps=1.5e-4
        )
        self.gradient_steps = 0

    def _tensors(self, batch: Transitions) -> dict[str, torch.Tensor]:
        types = {"masks": torch.bool, "next_masks": torch.bool, "actions": torch.long}
        return {
            name: torch.as_tensor(
                getattr(batch, name), dtype=types.get(name, torch.float32), device=self.device
            )
            for name in FIELDS
        }

    def update(self, batch: Transitions) -> dict[str, float]:
        """Take one gradient step on a batch. Return the loss and mean chosen Q-value."""
        data = self._tensors(batch)
        with torch.no_grad():
            targets = double_dqn_targets(
                self.online(data["next_obs"], data["next_masks"]),
                self.target(data["next_obs"], data["next_masks"]),
                data["rewards"],
                data["discounts"],
            )
        q_values = self.online(data["obs"], data["masks"])
        chosen = q_values.gather(-1, data["actions"].unsqueeze(-1)).squeeze(-1)
        loss = functional.smooth_l1_loss(chosen, targets)
        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.online.parameters(), self.config.max_grad_norm)
        self.optimizer.step()
        self.gradient_steps += 1
        if self.gradient_steps % self.config.target_update_every == 0:
            self.sync_target()
        return {"loss": loss.item(), "mean_q": chosen.mean().item()}

    def sync_target(self) -> None:
        """Copy the online weights into the target network."""
        self.target.load_state_dict(self.online.state_dict())
