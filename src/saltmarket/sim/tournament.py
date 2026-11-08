"""Tournaments: deterministic schedules, parallel play, and resumable chunked storage.

Each schedule is a list of matchups fixed by its parameters, and growing a parameter only
appends to the list. Finished chunks are skipped on restart, so a run can be stopped,
resumed, or extended with more games.
"""

import csv
import json
import multiprocessing
import os
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import numpy as np
from tqdm import tqdm

from saltmarket.bots.registry import make_any_bot
from saltmarket.engine import rules
from saltmarket.engine.game import Game
from saltmarket.engine.state import GameState

CHUNK_SIZE = 200
ROW_FIELDS = (
    "game_id", "table_size", "seat", "bot", "won", "turns", "hit_cap", "net_worth",
    "spaces_owned", "groups_completed", "groups_held_at_end", "peak_level", "bankrupt_cause",
)
GROUP_FIELDS = ("group", "rent_earned", "spent", "times_completed")


@dataclass(frozen=True, slots=True)
class Matchup:
    """One game: the bots in seat order and the seed."""

    game_id: int
    names: tuple[str, ...]
    seed: int


def round_robin_schedule(
    bots: Sequence[str], games_per_pair: int, base_seed: int
) -> list[Matchup]:
    """Pair every two bots, swapping who moves first on alternate games."""
    pairs = list(combinations(sorted(bots), 2))
    matchups = []
    for repeat in range(games_per_pair):
        for first, second in pairs:
            game_id = len(matchups)
            names = (first, second) if repeat % 2 == 0 else (second, first)
            matchups.append(Matchup(game_id, names, base_seed + game_id))
    return matchups


def random_table_schedule(
    bots: Sequence[str], tables: int, table_size: int, base_seed: int
) -> list[Matchup]:
    """Draw random tables of distinct bots, playing each in every rotated seat order."""
    pool = sorted(bots)
    matchups = []
    for table in range(tables):
        rng = np.random.default_rng([base_seed, table])
        drawn = [str(name) for name in rng.choice(pool, size=table_size, replace=False)]
        for shift in range(table_size):
            game_id = len(matchups)
            names = tuple(drawn[shift:] + drawn[:shift])
            matchups.append(Matchup(game_id, names, base_seed + game_id))
    return matchups


def _bankrupt_causes(state: GameState) -> dict[int, str]:
    return {
        player: "bank" if creditor is None else "player"
        for player, creditor in state.bankruptcies
    }


def play_matchup(matchup: Matchup) -> tuple[list[dict], dict[str, list[int]]]:
    """Play one game. Return a row per seat and rent, spend, and completion by group."""
    game = Game([make_any_bot(name) for name in matchup.names], seed=matchup.seed)
    result = game.play()
    state = game.state
    causes = _bankrupt_causes(state)
    completed_by: dict[int, list[str]] = {}
    for group, seat in state.first_completed.items():
        completed_by.setdefault(seat, []).append(group)
    rows = []
    for seat, name in enumerate(matchup.names):
        held = [g for g in state.board.groups if rules.owns_group(state, seat, g)]
        rows.append(
            {
                "game_id": matchup.game_id,
                "table_size": len(matchup.names),
                "seat": seat,
                "bot": name,
                "won": int(result.winner == seat),
                "turns": result.turns,
                "hit_cap": int(result.hit_cap),
                "net_worth": result.net_worths[seat],
                "spaces_owned": len(state.spaces_of(seat)),
                "groups_completed": "|".join(sorted(completed_by.get(seat, []))),
                "groups_held_at_end": "|".join(held),
                "peak_level": state.peak_level[seat],
                "bankrupt_cause": causes.get(seat, ""),
            }
        )
    groups = {
        group: [
            sum(state.rent_earned[i] for i in lots),
            sum(state.spent[i] for i in lots),
            int(group in state.first_completed),
        ]
        for group, lots in state.board.groups.items()
    }
    return rows, groups


def _write_csv(path: Path, fields: Sequence[str], rows: list) -> None:
    """Write through a temporary file so a stopped run never leaves half a chunk."""
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(fields)
        writer.writerows(rows)
    os.replace(temporary, path)


def _chunk_path(directory: Path, chunk: int) -> Path:
    return directory / f"chunk_{chunk:05d}.csv"


def run_chunk(directory: Path, chunk: int, matchups: list[Matchup]) -> int:
    """Play a chunk and save it. The rows file is written last and marks it complete."""
    rows: list[dict] = []
    totals: dict[str, list[int]] = {}
    for matchup in matchups:
        game_rows, groups = play_matchup(matchup)
        rows.extend(game_rows)
        for group, values in groups.items():
            current = totals.setdefault(group, [0, 0, 0])
            for position, value in enumerate(values):
                current[position] += value
    _write_csv(
        directory / f"groups_{chunk:05d}.csv",
        GROUP_FIELDS,
        [[group, *values] for group, values in totals.items()],
    )
    _write_csv(
        _chunk_path(directory, chunk),
        ROW_FIELDS,
        [[row[field] for field in ROW_FIELDS] for row in rows],
    )
    return len(matchups)


def _chunk_is_complete(path: Path, matchups: list[Matchup]) -> bool:
    """Return True if a chunk file holds every expected player row."""
    if not path.exists():
        return False
    expected = sum(len(m.names) for m in matchups)
    with path.open(encoding="utf-8") as file:
        return sum(1 for _ in file) - 1 == expected


def _check_manifest(directory: Path, manifest: dict) -> None:
    path = directory / "manifest.json"
    if path.exists() and json.loads(path.read_text(encoding="utf-8")) != manifest:
        raise ValueError(f"{directory} holds a different tournament. Use a new directory.")
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def run_tournament(
    schedule: list[Matchup],
    directory: Path,
    manifest: dict,
    workers: int,
    chunk_size: int = CHUNK_SIZE,
    progress: bool = True,
) -> int:
    """Play every unfinished chunk in parallel. Return the number of games played now.

    ``manifest`` identifies the tournament. It must not include the game count, so that
    a schedule can be extended, but anything that changes existing games belongs in it.

    Every game takes its seed from the schedule and every chunk goes to its own file, so
    the saved results are identical for any number of workers. One worker plays in this
    process, which skips the cost of starting a pool.
    """
    directory.mkdir(parents=True, exist_ok=True)
    _check_manifest(directory, manifest)
    chunks = [schedule[i : i + chunk_size] for i in range(0, len(schedule), chunk_size)]
    pending = [
        (number, chunk)
        for number, chunk in enumerate(chunks)
        if not _chunk_is_complete(_chunk_path(directory, number), chunk)
    ]
    total = sum(len(chunk) for _, chunk in pending)
    played = 0
    with tqdm(total=total, desc=directory.name, unit="game", disable=not progress) as bar:
        if workers <= 1:
            for number, chunk in pending:
                count = run_chunk(directory, number, chunk)
                played += count
                bar.update(count)
            return played
        context = multiprocessing.get_context("spawn")
        pool_size = min(workers, len(pending)) or 1
        with ProcessPoolExecutor(max_workers=pool_size, mp_context=context) as pool:
            futures = [pool.submit(run_chunk, directory, n, chunk) for n, chunk in pending]
            for future in as_completed(futures):
                count = future.result()
                played += count
                bar.update(count)
    return played
