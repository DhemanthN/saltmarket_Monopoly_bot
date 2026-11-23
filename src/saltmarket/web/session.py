"""One game for the website: human, agent and bot seats, paused at the human's decisions.

Pyodide has no threads, so the session pauses by replaying. It keeps the human's answers,
rebuilds the seeded game for every submit, and stops where an answer is missing. The same
seed and the same answers always give the same game, so the events written so far never
change and each replay only adds new ones. The replay costs about one game of compute.
"""

from collections.abc import Sequence
from pathlib import Path

from saltmarket.engine.game import GameResult
from saltmarket.paths import MODELS
from saltmarket.sim.digest import game_digest
from saltmarket.web.contract import (
    ActionId,
    Decision,
    GameEvent,
    SessionConfig,
    SubmitResult,
)
from saltmarket.web.observed import ObservedGame
from saltmarket.web.seats import AwaitingHuman, make_seat

MIN_SEATS = 2
MAX_SEATS = 4


class _Script:
    """Hands out recorded answers, then stops the game at the first unanswered decision."""

    def __init__(self, answers: list[ActionId]) -> None:
        self._answers = answers
        self._next = 0

    def __call__(self, decision: Decision) -> ActionId:
        if self._next == len(self._answers):
            raise AwaitingHuman(decision)
        self._next += 1
        return self._answers[self._next - 1]


class GameSession:
    """A seeded game that plays until the human must choose, then waits for ``submit``."""

    def __init__(
        self, seed: int, seats: Sequence[str], models_dir: Path = MODELS
    ) -> None:
        """Validate the table. Nothing is played until ``start``."""
        if not MIN_SEATS <= len(seats) <= MAX_SEATS:
            raise ValueError(f"A table needs {MIN_SEATS} to {MAX_SEATS} seats, got {len(seats)}")
        self.config = SessionConfig(seed, tuple(seats))
        self._models_dir = models_dir
        self._answers: list[ActionId] = []
        self._events: list[GameEvent] = []
        self._decision: Decision | None = None
        self._game: ObservedGame | None = None
        self._result: GameResult | None = None

    def start(self) -> None:
        """Play until the first human decision, or to the end if no seat is human."""
        self._replay()

    def current(self) -> Decision | None:
        """Return the pending human decision, or None if the game is over."""
        return self._decision

    def submit(self, action: ActionId) -> SubmitResult:
        """Answer the pending decision, then play on to the next one.

        An illegal id is rejected and changes nothing.
        """
        if self._result is not None:
            return SubmitResult(False, "game_over")
        if self._decision is None:
            return SubmitResult(False, "not_your_turn")
        if action not in {legal.id for legal in self._decision.legal}:
            return SubmitResult(False, "illegal")
        self._answers.append(action)
        self._replay()
        return SubmitResult(True)

    def events(self, since: int = 0) -> list[GameEvent]:
        """Return the events from index ``since`` on. The log only ever grows."""
        return self._events[since:]

    @property
    def result(self) -> GameResult | None:
        """The engine's result once the game is over, else None."""
        return self._result

    def fingerprint(self) -> str | None:
        """Return the same digest as ``sim.fingerprint`` once the game is over, else None."""
        if self._game is None or self._result is None:
            return None
        return game_digest(self._game)

    def final_state(self) -> dict[str, list]:
        """Return cash, ownership, buildings, mortgages and positions as they stand now."""
        if self._game is None:
            raise RuntimeError("Call start() first")
        state = self._game.state
        return {
            "cash": [p.cash for p in state.players],
            "owner": list(state.owner),
            "level": list(state.level),
            "mortgaged": list(state.mortgaged),
            "position": [p.position for p in state.players],
            "bankrupt": [p.bankrupt for p in state.players],
        }

    def _replay(self) -> None:
        script = _Script(self._answers)
        strategies = [
            make_seat(kind, len(self.config.seats), script, self._models_dir)
            for kind in self.config.seats
        ]
        game = ObservedGame(strategies, self.config.seed)
        try:
            result = game.play()
        except AwaitingHuman as pause:
            game.flush()
            self._decision = pause.decision
            self._result = None
        else:
            game.finish(result)
            self._decision = None
            self._result = result
        known = len(self._events)
        if game.events[:known] != self._events:
            raise RuntimeError("Replay changed events that were already shown")
        self._events.extend(game.events[known:])
        self._game = game

