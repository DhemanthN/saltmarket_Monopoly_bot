"""Exact fingerprints of seeded games, used to prove optimizations change nothing.

A fingerprint hashes the full event log and the final per-space tallies, so any change
to a single roll, card, bid, or payment in any turn changes it.
"""

import hashlib
from collections.abc import Sequence

import numpy as np

from saltmarket.bots.registry import make_any_bot
from saltmarket.engine.game import Game
from saltmarket.sim.tournament import Matchup

FINGERPRINT_SEED = 7_000_000


def fingerprint_schedule(bots: Sequence[str], games: int, table_size: int) -> list[Matchup]:
    """Return seeded games that seat every bot often, in a fixed order."""
    pool = sorted(bots)
    matchups = []
    for game_id in range(games):
        rng = np.random.default_rng([FINGERPRINT_SEED, table_size, game_id])
        names = tuple(str(name) for name in rng.choice(pool, size=table_size, replace=False))
        matchups.append(Matchup(game_id, names, FINGERPRINT_SEED + 1000 * table_size + game_id))
    return matchups


def game_fingerprint(matchup: Matchup) -> dict:
    """Play one game with its event log on and return its outcome and a hash of everything."""
    game = Game([make_any_bot(name) for name in matchup.names], seed=matchup.seed, record_log=True)
    result = game.play()
    state = game.state
    digest = hashlib.sha256()
    for event in game.log or ():
        digest.update(repr(event).encode())
        digest.update(b"\n")
    for tally in (state.visits, state.rent_earned, state.spent, state.owner, state.level,
                  state.mortgaged, [p.cash for p in state.players], state.peak_level):
        digest.update(repr(list(tally)).encode())
    digest.update(repr(sorted(state.first_completed.items())).encode())
    digest.update(repr(state.bankruptcies).encode())
    return {
        "game_id": matchup.game_id,
        "names": list(matchup.names),
        "seed": matchup.seed,
        "winner": result.winner,
        "turns": result.turns,
        "hit_cap": result.hit_cap,
        "net_worths": list(result.net_worths),
        "sha256": digest.hexdigest(),
    }
