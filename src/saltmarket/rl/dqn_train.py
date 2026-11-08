"""The DQN training loop: same curriculum, opponents, and step budget as PPO.

Each round, worker processes play games with an epsilon-greedy copy of the Q-network
while the main process takes gradient steps on the GPU using the previous round's data.
Collection therefore uses weights that are one round old, which DQN tolerates because it
learns off-policy.
"""

import multiprocessing
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

from saltmarket.rl import encoding as enc
from saltmarket.rl.dqn import DQN, DQNConfig, ReplayBuffer
from saltmarket.rl.dqn_workers import DQNRequest, Experience, dqn_worker_main, merge_transitions
from saltmarket.rl.train import append_log, episode_stats, stage_at
from saltmarket.rl.workers import TableSpec

LOG_FIELDS = (
    "round", "steps", "stage", "episodes", "win_rate", "win_rate_2p", "win_rate_4p",
    "cap_rate", "mean_return", "epsilon", "loss", "mean_q", "gradient_steps",
    "buffer_size", "learn_seconds", "seconds",
)


@dataclass(frozen=True, slots=True)
class DQNTrainConfig:
    """Settings for one DQN training run.

    ``snapshot_every_steps`` matches PPO, which saved a snapshot every 25 updates of
    40,960 decisions. ``replay_ratio`` is how many times, on average, each collected
    transition is used in a gradient step.
    """

    total_steps: int
    workers: int = 20
    steps_per_worker: int = 512
    seed: int = 0
    shaping: float = 0.2
    snapshot_every_steps: int = 1_024_000
    max_snapshots: int = 5
    checkpoint_every: int = 50
    opponent_counts: tuple[int, ...] = (1,)
    device: str = "cuda"
    epsilon_start: float = 1.0
    epsilon_end: float = 0.02
    epsilon_fraction: float = 0.1
    learning_starts: int = 50_000
    replay_ratio: float = 4.0


def epsilon_at(config: DQNTrainConfig, fraction: float) -> float:
    """Return the exploration rate, falling linearly and then holding steady."""
    progress = min(1.0, fraction / config.epsilon_fraction) if config.epsilon_fraction else 1.0
    return config.epsilon_start + progress * (config.epsilon_end - config.epsilon_start)


def updates_for(collected: int, replay_ratio: float, batch_size: int) -> int:
    """Return how many gradient steps reuse ``collected`` transitions ``replay_ratio`` times."""
    return round(collected * replay_ratio / batch_size)


@dataclass(slots=True)
class _Progress:
    round: int = 0
    steps: int = 0
    seconds: float = 0.0
    pending_updates: int = 0
    snapshots: list | None = None


def _save_checkpoint(out_dir: Path, dqn: DQN, buffer: ReplayBuffer, progress: _Progress) -> None:
    """Save networks, optimizer, counters, snapshots, and the replay buffer atomically."""
    replay = out_dir / "replay.tmp.npz"
    np.savez(replay, **buffer.state_dict())
    replay.replace(out_dir / "replay.npz")
    temporary = out_dir / "latest.tmp"
    torch.save(
        {
            "online": dqn.online.state_dict(),
            "target": dqn.target.state_dict(),
            "optimizer": dqn.optimizer.state_dict(),
            "gradient_steps": dqn.gradient_steps,
            "round": progress.round,
            "steps": progress.steps,
            "seconds": progress.seconds,
            "pending_updates": progress.pending_updates,
            "snapshots": progress.snapshots,
        },
        temporary,
    )
    temporary.replace(out_dir / "latest.pt")


def _load_checkpoint(
    out_dir: Path, dqn: DQN, buffer: ReplayBuffer, device: str
) -> _Progress:
    checkpoint = out_dir / "latest.pt"
    if not checkpoint.exists():
        return _Progress(snapshots=[])
    saved = torch.load(checkpoint, map_location=device, weights_only=False)
    dqn.online.load_state_dict(saved["online"])
    dqn.target.load_state_dict(saved["target"])
    dqn.optimizer.load_state_dict(saved["optimizer"])
    dqn.gradient_steps = saved["gradient_steps"]
    with np.load(out_dir / "replay.npz") as data:
        buffer.load_state_dict(dict(data))
    return _Progress(
        saved["round"], saved["steps"], saved["seconds"], saved["pending_updates"],
        saved["snapshots"],
    )


def _learn(dqn: DQN, buffer: ReplayBuffer, updates: int, rng: np.random.Generator) -> dict:
    totals = {"loss": 0.0, "mean_q": 0.0}
    for _ in range(updates):
        metrics = dqn.update(buffer.sample(dqn.config.batch_size, rng))
        for name in totals:
            totals[name] += metrics[name]
    if not updates:
        return {name: float("nan") for name in totals}
    return {name: total / updates for name, total in totals.items()}


def train_dqn(
    config: DQNTrainConfig, dqn_config: DQNConfig, out_dir: Path, log_path: Path
) -> DQN:
    """Train until ``total_steps``, resuming from ``out_dir`` if a checkpoint exists."""
    out_dir.mkdir(parents=True, exist_ok=True)
    dqn = DQN(enc.OBS_SIZE, enc.NUM_ACTIONS, dqn_config, config.device, config.seed)
    buffer = ReplayBuffer(dqn_config.buffer_size, enc.OBS_SIZE, enc.NUM_ACTIONS)
    progress = _load_checkpoint(out_dir, dqn, buffer, config.device)
    round_steps = config.workers * config.steps_per_worker

    context = multiprocessing.get_context("spawn")
    connections, processes = [], []
    for worker in range(config.workers):
        parent, child = context.Pipe()
        seed = config.seed * 100_003 + progress.round * 1_009 + worker
        process = context.Process(
            target=dqn_worker_main,
            args=(child, seed, config.shaping, dqn_config.gamma, dqn_config.n_step),
            daemon=True,
        )
        process.start()
        connections.append(parent)
        processes.append(process)

    started = time.perf_counter()
    try:
        while progress.steps < config.total_steps:
            fraction = progress.steps / config.total_steps
            stage = stage_at(fraction)
            epsilon = epsilon_at(config, fraction)
            spec = TableSpec(
                list(stage.pool), progress.snapshots, stage.snapshot_share,
                config.opponent_counts,
            )
            request = DQNRequest(
                dqn.online.numpy_weights(), spec, config.steps_per_worker, epsilon
            )
            for connection in connections:
                connection.send(request)
            learn_started = time.perf_counter()
            rng = np.random.default_rng([config.seed, progress.round])
            metrics = _learn(dqn, buffer, progress.pending_updates, rng)
            learn_seconds = time.perf_counter() - learn_started
            experiences: list[Experience] = [connection.recv() for connection in connections]
            batch = merge_transitions([e.transitions for e in experiences])
            buffer.add(batch)

            previous_steps = progress.steps
            progress.round += 1
            progress.steps += round_steps
            progress.pending_updates = (
                updates_for(len(batch), config.replay_ratio, dqn_config.batch_size)
                if len(buffer) >= config.learning_starts
                else 0
            )
            progress.seconds = progress.seconds + time.perf_counter() - started
            started = time.perf_counter()
            infos = [info for e in experiences for info in e.episode_infos]
            returns = [value for e in experiences for value in e.episode_returns]
            row = {
                "round": progress.round,
                "steps": progress.steps,
                "stage": stage.name,
                **episode_stats(infos, returns),
                "epsilon": epsilon,
                **metrics,
                "gradient_steps": dqn.gradient_steps,
                "buffer_size": len(buffer),
                "learn_seconds": learn_seconds,
                "seconds": progress.seconds,
            }
            append_log(log_path, row, LOG_FIELDS)
            every = config.snapshot_every_steps
            if progress.steps // every > previous_steps // every:
                progress.snapshots = [*progress.snapshots, dqn.online.numpy_weights()][
                    -config.max_snapshots :
                ]
            if progress.round % config.checkpoint_every == 0:
                _save_checkpoint(out_dir, dqn, buffer, progress)
        progress.seconds = progress.seconds + time.perf_counter() - started
        _save_checkpoint(out_dir, dqn, buffer, progress)
    finally:
        for connection in connections:
            connection.send(None)
        for process in processes:
            process.join(timeout=10)
            if process.is_alive():
                process.terminate()
    return dqn
