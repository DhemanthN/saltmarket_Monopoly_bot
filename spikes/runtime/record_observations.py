"""Record 100 desktop (observation, mask) pairs and the desktop greedy actions for them."""

from pathlib import Path

import numpy as np

from saltmarket.bots.registry import make_any_bot
from saltmarket.engine.game import Game
from saltmarket.rl.agent import AgentStrategy
from saltmarket.rl.policy import MASKED_LOGIT, NumpyPolicy, _forward
from saltmarket.rl.train import load_policy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
COUNT = 100
EVERY = 7


def main() -> None:
    """Play seeded 2-player games with random legal choices and keep every 7th decision."""
    obs_rows, mask_rows = [], []
    for seed in range(1000, 1200):
        rng = np.random.default_rng(seed)
        counter = 0

        def decide(obs: np.ndarray, mask: np.ndarray, rng: np.random.Generator = rng) -> int:
            nonlocal counter
            counter += 1
            if counter % EVERY == 0 and len(obs_rows) < COUNT:
                obs_rows.append(obs.copy())
                mask_rows.append(mask.copy())
            return int(rng.choice(np.flatnonzero(mask)))

        Game([AgentStrategy(decide), make_any_bot("cash_hoarder")], seed=seed).play()
        if len(obs_rows) >= COUNT:
            break
    obs, masks = np.array(obs_rows), np.array(mask_rows)
    arrays = {"obs": obs, "masks": masks}
    for name, file in (("ppo", "two_player.npz"), ("dqn", "dqn_two_player.npz")):
        weights = load_policy(ROOT / "models" / file)
        policy = NumpyPolicy(weights)
        pairs = list(zip(obs, masks, strict=True))
        arrays[f"{name}_actions"] = np.array([policy.greedy(o, m) for o, m in pairs])
        arrays[f"{name}_logits"] = np.array(
            [np.where(m, _forward(weights.actor, o), MASKED_LOGIT) for o, m in pairs]
        )
    np.savez_compressed(HERE / "fixtures" / "observations.npz", **arrays)
    print(obs.shape, {k: v.shape for k, v in arrays.items()})


if __name__ == "__main__":
    main()
