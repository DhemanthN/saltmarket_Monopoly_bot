"""The hash of a finished game, kept free of tournament imports so the web runtime stays small."""

import hashlib

from saltmarket.engine.game import Game


def game_digest(game: Game) -> str:
    """Return a sha256 of a finished game's event log and final per-space tallies.

    The game must have been created with ``record_log=True``. Any change to a single roll,
    card, bid, or payment in any turn changes the digest.
    """
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
    return digest.hexdigest()
