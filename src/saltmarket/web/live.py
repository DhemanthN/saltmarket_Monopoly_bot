"""One game played straight through for the browser worker, with a blocking human seat.

The replay ``GameSession`` rebuilds the game on every submit. In the Web Worker the human's
``answer`` can block instead (the worker waits on ``Atomics.wait`` until the page answers), so
the game runs exactly once. Events cross to JavaScript as JSON text: before each human decision,
and once more at the end. Both paths use the same seats and ``ObservedGame``, so a seed and a
list of answers give the same events and fingerprint either way.
"""

import json
from collections.abc import Callable, Sequence
from pathlib import Path

from saltmarket.engine.game import GameResult
from saltmarket.paths import MODELS
from saltmarket.sim.digest import game_digest
from saltmarket.web import contract as c
from saltmarket.web.observed import ObservedGame
from saltmarket.web.seats import make_seat

AskHuman = Callable[[str], int]
"""Receives a ``Decision`` as JSON text and returns the chosen action id."""

Emit = Callable[[str], None]
"""Receives a JSON list of new events."""


def final_state(game: ObservedGame) -> c.FinalState:
    """Return cash, ownership, buildings, mortgages and positions as they stand now."""
    state = game.state
    return c.FinalState(
        cash=tuple(p.cash for p in state.players),
        owner=tuple(state.owner),
        level=tuple(state.level),
        mortgaged=tuple(state.mortgaged),
        position=tuple(p.position for p in state.players),
        bankrupt=tuple(p.bankrupt for p in state.players),
    )


def result_view(result: GameResult) -> c.ResultView:
    """Return the engine result in contract form."""
    return c.ResultView(
        result.winner, result.turns, result.hit_cap, result.net_worths, result.bankrupt
    )


class _Feed:
    """Sends every event the game has written since the last send."""

    def __init__(self, emit: Emit) -> None:
        self._emit = emit
        self._sent = 0
        self.game: ObservedGame | None = None

    def send(self) -> None:
        assert self.game is not None
        fresh = self.game.events[self._sent:]
        if fresh:
            self._emit(json.dumps([c.to_json(e) for e in fresh], separators=(",", ":")))
            self._sent += len(fresh)


def play_live(
    seed: int,
    seats: Sequence[str],
    ask: AskHuman,
    emit: Emit,
    answers: Sequence[c.ActionId] = (),
    models_dir: Path = MODELS,
) -> str:
    """Play one game to the end and return the result, fingerprint and final state as JSON.

    ``answers`` are given to the first human decisions without calling ``ask``. A worker that
    restarts after an error uses them to rebuild the game the person was playing.
    """
    feed = _Feed(emit)
    replay = list(answers)

    def answer(decision: c.Decision) -> c.ActionId:
        assert feed.game is not None
        feed.game.flush()
        feed.send()
        if replay:
            return replay.pop(0)
        return ask(json.dumps(c.to_json(decision), separators=(",", ":")))

    strategies = [make_seat(kind, len(seats), answer, models_dir) for kind in seats]
    game = ObservedGame(strategies, seed)
    feed.game = game
    result = game.play()
    game.finish(result)
    feed.send()
    summary = {
        "result": c.to_json(result_view(result)),
        "fingerprint": game_digest(game),
        "finalState": c.to_json(final_state(game)),
    }
    return json.dumps(summary, separators=(",", ":"))
