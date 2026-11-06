"""Held-out evaluation of a trained policy against the bot pool.

A "matchup" here means one complete game. 2-player evaluation plays the agent against
each bot in turn, alternating who moves first. 4-player evaluation seats the agent with
three distinct bots drawn from the pool and rotates the table through every seat order.
Seeds start at EVAL_SEED_BASE, a range training never uses.
"""

import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from functools import partial

import numpy as np
import pandas as pd
from tqdm import tqdm

from saltmarket.analysis.tournament_stats import wilson_interval
from saltmarket.bots.catalog import make_bot
from saltmarket.engine.game import Game
from saltmarket.rl.agent import AgentStrategy
from saltmarket.rl.policy import NumpyPolicy, PolicyWeights

EVAL_SEED_BASE = 9_000_000_000
FRESH_SEED_OFFSET = 100_000_000
AGENT = "ppo"
CHUNK_SIZE = 100


@dataclass(frozen=True, slots=True)
class EvalGame:
    """One evaluation game: seats in order, with AGENT marking the agent."""

    game_id: int
    seats: tuple[str, ...]
    seed: int


def two_player_schedule(
    bots: list[str], games_per_bot: int, seed_offset: int = 0
) -> list[EvalGame]:
    """Play each bot ``games_per_bot`` times, alternating seats."""
    games = []
    base = EVAL_SEED_BASE + seed_offset
    for repeat in range(games_per_bot):
        for bot in sorted(bots):
            seats = (AGENT, bot) if repeat % 2 == 0 else (bot, AGENT)
            games.append(EvalGame(len(games), seats, base + len(games)))
    return games


def four_player_schedule(bots: list[str], tables: int, seed_offset: int = 0) -> list[EvalGame]:
    """Seat the agent with three distinct bots, playing all four rotations of each table."""
    pool = sorted(bots)
    games = []
    base = EVAL_SEED_BASE + 1_000_000 + seed_offset
    for table in range(tables):
        rng = np.random.default_rng([base, table])
        drawn = [AGENT, *(str(name) for name in rng.choice(pool, size=3, replace=False))]
        for shift in range(4):
            seats = tuple(drawn[shift:] + drawn[:shift])
            games.append(EvalGame(len(games), seats, base + len(games)))
    return games


def play_eval_games(
    games: list[EvalGame], weights: PolicyWeights, greedy: bool
) -> list[dict]:
    """Play games with the agent and return one row per game."""
    policy = NumpyPolicy(weights)
    rows = []
    for game in games:
        rng = np.random.default_rng(game.seed)
        if greedy:
            agent = AgentStrategy(policy.greedy)
        else:
            agent = AgentStrategy(lambda obs, mask, r=rng: policy.sample(obs, mask, r)[0])
        seat = game.seats.index(AGENT)
        bots = [agent if name == AGENT else make_bot(name) for name in game.seats]
        result = Game(bots, seed=game.seed).play()
        rows.append(
            {
                "game_id": game.game_id,
                "table_size": len(game.seats),
                "seat": seat,
                "opponents": "|".join(sorted(n for n in game.seats if n != AGENT)),
                "won": int(result.winner == seat),
                "hit_cap": int(result.hit_cap),
                "turns": result.turns,
                "agent_bankrupt": int(result.bankrupt[seat]),
            }
        )
    return rows


def run_evaluation(
    schedule: list[EvalGame], weights: PolicyWeights, workers: int, greedy: bool = True
) -> pd.DataFrame:
    """Play a schedule in parallel and return per-game rows."""
    chunks = [schedule[i : i + CHUNK_SIZE] for i in range(0, len(schedule), CHUNK_SIZE)]
    context = multiprocessing.get_context("spawn")
    play = partial(play_eval_games, weights=weights, greedy=greedy)
    rows: list[dict] = []
    with ProcessPoolExecutor(max_workers=workers, mp_context=context) as pool:
        for part in tqdm(pool.map(play, chunks), total=len(chunks), unit="chunk"):
            rows.extend(part)
    return pd.DataFrame(rows)


def summarize_wins(frame: pd.DataFrame) -> dict[str, float]:
    """Return win rates with 95% intervals, over all games and over decided games."""
    decided = frame[frame["hit_cap"] == 0]
    wins, games = int(frame["won"].sum()), len(frame)
    decided_wins, decided_games = int(decided["won"].sum()), len(decided)
    low, high = wilson_interval(wins, games)
    decided_low, decided_high = wilson_interval(decided_wins, decided_games)
    return {
        "games": games,
        "wins": wins,
        "win_rate": wins / games if games else float("nan"),
        "ci_low": low,
        "ci_high": high,
        "decided_games": decided_games,
        "decided_wins": decided_wins,
        "decided_win_rate": decided_wins / decided_games if decided_games else float("nan"),
        "decided_ci_low": decided_low,
        "decided_ci_high": decided_high,
        "cap_rate": float(frame["hit_cap"].mean()),
    }


def per_opponent(frame: pd.DataFrame) -> pd.DataFrame:
    """Return the agent's results against each bot it faced, including shared tables."""
    exploded = frame.assign(opponent=frame["opponents"].str.split("|")).explode("opponent")
    records = [
        {"opponent": name, **summarize_wins(part)} for name, part in exploded.groupby("opponent")
    ]
    return pd.DataFrame(records).sort_values("win_rate", ignore_index=True)


def compare_with_bots(bots: pd.DataFrame, agent: dict[str, float], label: str) -> pd.DataFrame:
    """Rank the agent among the tournament bots, over all games and decided games.

    The two sets of games are close but not identical: a bot's tournament games exclude
    itself and the agent, while the agent's evaluation games face all of the bots.
    """
    capped_games = agent["games"] - agent["decided_games"]
    capped_wins = agent["wins"] - agent["decided_wins"]
    row = {
        "bot": label,
        "win_rate": agent["win_rate"],
        "ci_low": agent["ci_low"],
        "ci_high": agent["ci_high"],
        "decided_win_rate": agent["decided_win_rate"],
        "cap_rate": agent["cap_rate"],
        "capped_win_rate": capped_wins / capped_games if capped_games else float("nan"),
    }
    table = bots.assign(
        capped_win_rate=(bots["wins"] - bots["decided_wins"])
        / (bots["games"] - bots["decided_games"]).replace(0, float("nan"))
    )[list(row)]
    table = pd.concat([table, pd.DataFrame([row])], ignore_index=True)
    table["rank"] = table["win_rate"].rank(ascending=False, method="min").astype(int)
    table["decided_rank"] = table["decided_win_rate"].rank(ascending=False, method="min")
    table["decided_rank"] = table["decided_rank"].astype(int)
    return table.sort_values("rank", ignore_index=True)
