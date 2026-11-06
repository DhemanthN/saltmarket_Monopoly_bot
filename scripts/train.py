"""Train the PPO agent. Rerunning with the same --run resumes from its checkpoint.

Usage: python scripts/train.py --steps 20000000 --run main
Checkpoints go to checkpoints/<run>/, the log to results/training_log_<run>.csv, and the
final weights to models/<run>.npz.
"""

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Parse arguments and run training."""
    from saltmarket.rl.ppo import PPOConfig
    from saltmarket.rl.train import TrainConfig, save_policy, train

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, required=True)
    parser.add_argument("--run", default="main")
    parser.add_argument("--workers", type=int, default=20)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--shaping", type=float, default=0.2)
    args = parser.parse_args()

    config = TrainConfig(args.steps, args.workers, seed=args.seed, shaping=args.shaping)
    log_path = ROOT / "results" / f"training_log_{args.run}.csv"
    ppo = train(config, PPOConfig(), ROOT / "checkpoints" / args.run, log_path)
    (ROOT / "models").mkdir(exist_ok=True)
    save_policy(ppo.model.numpy_weights(), ROOT / "models" / f"{args.run}.npz")


if __name__ == "__main__":
    main()
