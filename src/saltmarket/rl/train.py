"""The training loop: curriculum, parallel rollouts, logging, and checkpoints."""

import csv
import multiprocessing
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

from saltmarket.bots.catalog import BOTS
from saltmarket.rl import encoding as enc
from saltmarket.rl.policy import PolicyWeights
from saltmarket.rl.ppo import PPO, PPOConfig
from saltmarket.rl.rollout import Rollout, merge_batches
from saltmarket.rl.workers import OPPONENT_COUNTS, RolloutRequest, TableSpec, worker_main

LOG_FIELDS = (
    "update", "steps", "stage", "episodes", "win_rate", "win_rate_2p", "win_rate_4p",
    "cap_rate", "mean_return", "policy_loss", "value_loss", "entropy", "clip_fraction",
    "seconds",
)
SIMPLE_POOL = ("always_buy", "balanced", "cash_hoarder", "random", "three_depots")


@dataclass(frozen=True, slots=True)
class Stage:
    """One curriculum stage, active from ``start`` as a fraction of total steps."""

    name: str
    start: float
    pool: tuple[str, ...]
    snapshot_share: float = 0.0


CURRICULUM = (
    Stage("random", 0.0, ("random", "never_buy")),
    Stage("simple", 0.05, SIMPLE_POOL),
    Stage("full", 0.2, tuple(sorted(BOTS))),
    Stage("self_play", 0.6, tuple(sorted(BOTS)), snapshot_share=0.3),
)


def stage_at(fraction: float) -> Stage:
    """Return the curriculum stage for a share of training completed."""
    return [stage for stage in CURRICULUM if stage.start <= fraction][-1]


def resolve_device(requested: str) -> str:
    """Return a usable device, refusing to fall back silently from CUDA to the CPU."""
    if requested.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available. Pass --device cpu to train on the CPU.")
    return requested


@dataclass(frozen=True, slots=True)
class TrainConfig:
    """Settings for one training run."""

    total_steps: int
    workers: int = 20
    steps_per_worker: int = 2048
    seed: int = 0
    shaping: float = 0.2
    snapshot_every: int = 25
    max_snapshots: int = 5
    checkpoint_every: int = 10
    opponent_counts: tuple[int, ...] = OPPONENT_COUNTS
    device: str = "cuda"


def _win_rate(infos: list[dict], size: int | None = None) -> float:
    chosen = [i["won"] for i in infos if size is None or i["table_size"] == size]
    return float(np.mean(chosen)) if chosen else float("nan")


def _log_row(
    update: int, steps: int, stage: Stage, rollouts: list[Rollout], metrics: dict, seconds: float
) -> dict:
    infos = [info for rollout in rollouts for info in rollout.episode_infos]
    returns = [value for rollout in rollouts for value in rollout.episode_returns]
    return {
        "update": update,
        "steps": steps,
        "stage": stage.name,
        "episodes": len(infos),
        "win_rate": _win_rate(infos),
        "win_rate_2p": _win_rate(infos, 2),
        "win_rate_4p": _win_rate(infos, 4),
        "cap_rate": float(np.mean([i["hit_cap"] for i in infos])) if infos else float("nan"),
        "mean_return": float(np.mean(returns)) if returns else float("nan"),
        **metrics,
        "seconds": seconds,
    }


def _append_log(path: Path, row: dict) -> None:
    new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, LOG_FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow(row)


def save_policy(weights: PolicyWeights, path: Path) -> None:
    """Save network weights as a small NumPy archive for evaluation."""
    arrays = {}
    for name, layers in (("actor", weights.actor), ("critic", weights.critic)):
        for position, (weight, bias) in enumerate(layers):
            arrays[f"{name}_{position}_w"] = weight
            arrays[f"{name}_{position}_b"] = bias
    np.savez_compressed(path, **arrays)


def load_policy(path: Path) -> PolicyWeights:
    """Load network weights saved by ``save_policy``."""
    with np.load(path) as data:
        def layers(name: str) -> tuple:
            count = sum(key.startswith(name) and key.endswith("_w") for key in data.files)
            return tuple(
                (data[f"{name}_{i}_w"], data[f"{name}_{i}_b"]) for i in range(count)
            )

        return PolicyWeights(layers("actor"), layers("critic"))


def _save_checkpoint(
    path: Path, ppo: PPO, update: int, steps: int, seconds: float, snapshots: list
) -> None:
    temporary = path.with_suffix(".tmp")
    torch.save(
        {
            "model": ppo.model.state_dict(),
            "optimizer": ppo.optimizer.state_dict(),
            "update": update,
            "steps": steps,
            "seconds": seconds,
            "snapshots": snapshots,
        },
        temporary,
    )
    temporary.replace(path)


def train(config: TrainConfig, ppo_config: PPOConfig, out_dir: Path, log_path: Path) -> PPO:
    """Train until ``total_steps``, resuming from ``out_dir`` if a checkpoint exists."""
    out_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = out_dir / "latest.pt"
    ppo = PPO(enc.OBS_SIZE, enc.NUM_ACTIONS, ppo_config, config.device, config.seed)
    update, steps, elapsed, snapshots = 0, 0, 0.0, []
    if checkpoint.exists():
        saved = torch.load(checkpoint, map_location=config.device, weights_only=False)
        ppo.model.load_state_dict(saved["model"])
        ppo.optimizer.load_state_dict(saved["optimizer"])
        update, steps = saved["update"], saved["steps"]
        elapsed, snapshots = saved["seconds"], saved["snapshots"]

    context = multiprocessing.get_context("spawn")
    connections, processes = [], []
    for worker in range(config.workers):
        parent, child = context.Pipe()
        seed = config.seed * 100_003 + update * 1_009 + worker
        process = context.Process(
            target=worker_main,
            args=(child, seed, config.shaping, ppo_config.gamma),
            daemon=True,
        )
        process.start()
        connections.append(parent)
        processes.append(process)

    started = time.perf_counter()
    try:
        while steps < config.total_steps:
            stage = stage_at(steps / config.total_steps)
            spec = TableSpec(
                list(stage.pool), snapshots, stage.snapshot_share, config.opponent_counts
            )
            weights = ppo.model.numpy_weights()
            request = RolloutRequest(
                weights, spec, config.steps_per_worker, ppo_config.gamma, ppo_config.gae_lambda
            )
            for connection in connections:
                connection.send(request)
            rollouts = [connection.recv() for connection in connections]
            metrics = ppo.update(merge_batches([rollout.batch for rollout in rollouts]))
            update += 1
            steps += config.workers * config.steps_per_worker
            seconds = elapsed + time.perf_counter() - started
            _append_log(log_path, _log_row(update, steps, stage, rollouts, metrics, seconds))
            if update % config.snapshot_every == 0:
                snapshots = [*snapshots, ppo.model.numpy_weights()][-config.max_snapshots :]
            if update % config.checkpoint_every == 0:
                _save_checkpoint(checkpoint, ppo, update, steps, seconds, snapshots)
        seconds = elapsed + time.perf_counter() - started
        _save_checkpoint(checkpoint, ppo, update, steps, seconds, snapshots)
    finally:
        for connection in connections:
            connection.send(None)
        for process in processes:
            process.join(timeout=10)
            if process.is_alive():
                process.terminate()
    return ppo
