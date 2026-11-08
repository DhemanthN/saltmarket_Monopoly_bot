"""Train the DQN agent. Rerunning with the same --run resumes from its checkpoint.

Usage: python scripts/train_dqn.py --steps 20000000 --run dqn_two_player
Defaults match the PPO two_player run: 2-player tables, the same curriculum, and the same
seed and shaping. Checkpoints go to checkpoints/<run>/, the log to
results/training_log_<run>.csv, and the final weights to models/<run>.npz.
"""

import argparse

from saltmarket.paths import CHECKPOINTS, MODELS, RESULTS


def main() -> None:
    """Parse arguments and run training."""
    import torch

    from saltmarket.rl.dqn import DQNConfig
    from saltmarket.rl.dqn_train import DQNTrainConfig, train_dqn
    from saltmarket.rl.train import resolve_device, save_policy

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, required=True)
    parser.add_argument("--run", default="dqn_two_player")
    parser.add_argument("--workers", type=int, default=20)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--shaping", type=float, default=0.2)
    parser.add_argument(
        "--opponents", type=int, nargs="+", default=[1], help="Opponents per table."
    )
    parser.add_argument("--device", default="cuda", help="cuda (default) or cpu.")
    args = parser.parse_args()

    device = resolve_device(args.device)
    name = torch.cuda.get_device_name(device) if device.startswith("cuda") else "CPU"
    print(f"Network updates run on: {name}", flush=True)
    config = DQNTrainConfig(
        args.steps,
        args.workers,
        seed=args.seed,
        shaping=args.shaping,
        opponent_counts=tuple(args.opponents),
        device=device,
    )
    RESULTS.mkdir(parents=True, exist_ok=True)
    MODELS.mkdir(parents=True, exist_ok=True)
    log_path = RESULTS / f"training_log_{args.run}.csv"
    dqn = train_dqn(config, DQNConfig(), CHECKPOINTS / args.run, log_path)
    save_policy(dqn.online.numpy_weights(), MODELS / f"{args.run}.npz")


if __name__ == "__main__":
    main()
