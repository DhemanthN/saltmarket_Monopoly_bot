"""Measure how often each held-out bot plays a game exactly as some training bot would.

Usage: python scripts/heldout_overlap.py --seeds 4
Every bot plays 2-player games against each of the 26 training bots, in both seats, on the
same seeds. Two bots "play identically" in a game when the full event logs match, which
means every decision was the same. For each held-out bot this reports the training bot it
matches most often. Writes results/heldout_overlap.csv.
"""

import argparse
import hashlib
import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor

import pandas as pd

from saltmarket.bots.catalog import BOTS
from saltmarket.bots.heldout.catalog import HELDOUT_BOTS
from saltmarket.bots.registry import make_any_bot
from saltmarket.engine.game import Game
from saltmarket.paths import RESULTS

OVERLAP_SEED = 8_000_000


def game_hashes(task: tuple[str, int]) -> tuple[str, list[str]]:
    """Play one bot against every training bot and return a hash of each game's log."""
    subject, seeds = task
    hashes = []
    for opponent in sorted(BOTS):
        for seed in range(seeds):
            for seat in (0, 1):
                names = [subject, opponent] if seat == 0 else [opponent, subject]
                game = Game([make_any_bot(name) for name in names],
                            seed=OVERLAP_SEED + seed, record_log=True)
                game.play()
                hashes.append(hashlib.sha256(repr(game.log).encode()).hexdigest())
    return subject, hashes


def overlap_table(hashes: dict[str, list[str]]) -> pd.DataFrame:
    """Return, for each held-out bot, its closest training bot and the identical share."""
    rows = []
    for heldout in sorted(HELDOUT_BOTS):
        shares = {
            bot: sum(a == b for a, b in zip(hashes[heldout], hashes[bot], strict=True))
            / len(hashes[heldout])
            for bot in sorted(BOTS)
        }
        closest = max(shares, key=shares.get)
        rows.append({"heldout_bot": heldout, "closest_training_bot": closest,
                     "identical_share": shares[closest], "games": len(hashes[heldout])})
    return pd.DataFrame(rows).sort_values("identical_share", ascending=False, ignore_index=True)


def main() -> None:
    """Play every bot's games in parallel and save the overlap table."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=4)
    parser.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    args = parser.parse_args()

    tasks = [(name, args.seeds) for name in sorted({**BOTS, **HELDOUT_BOTS})]
    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=args.workers, mp_context=context) as pool:
        hashes = dict(pool.map(game_hashes, tasks))
    table = overlap_table(hashes)
    RESULTS.mkdir(parents=True, exist_ok=True)
    table.to_csv(RESULTS / "heldout_overlap.csv", index=False, float_format="%.4f")
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
