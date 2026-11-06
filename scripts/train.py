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
    import torch

    from saltmarket.rl.ppo import PPOConfig
    from saltmarket.rl.train import TrainConfig, resolve_device, save_policy, train

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, required=True)
    parser.add_argument("--run", default="main")
    parser.add_argument("--workers", type=int, default=20)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--shaping", type=float, default=0.2)
    parser.add_argument(
        "--opponents", type=int, nargs="+", default=[1, 3], help="Opponents per table."
    )
    parser.add_argument("--device", default="cuda", help="cuda (default) or cpu.")
    args = parser.parse_args()

    device = resolve_device(args.device)
    name = torch.cuda.get_device_name(device) if device.startswith("cuda") else "CPU"
    print(f"Network updates run on: {name}", flush=True)
    config = TrainConfig(
        args.steps,
        args.workers,
        seed=args.seed,
        shaping=args.shaping,
        opponent_counts=tuple(args.opponents),
        device=device,
    )
    log_path = ROOT / "results" / f"training_log_{args.run}.csv"
    ppo = train(config, PPOConfig(), ROOT / "checkpoints" / args.run, log_path)
    (ROOT / "models").mkdir(exist_ok=True)
    save_policy(ppo.model.numpy_weights(), ROOT / "models" / f"{args.run}.npz")


if __name__ == "__main__":
    main()
