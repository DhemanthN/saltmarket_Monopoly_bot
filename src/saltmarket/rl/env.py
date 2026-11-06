"""Gymnasium environment around the game.

The game loop calls strategies directly, so it cannot pause mid-turn on its own. The env
runs each game on a worker thread and hands control back and forth at every decision.
Exactly one side runs at a time, which keeps games deterministic.
"""

import threading
from collections.abc import Callable
from queue import SimpleQueue

import gymnasium as gym
import numpy as np

from saltmarket.bots.base import Strategy
from saltmarket.engine import rules
from saltmarket.engine.config import GameConfig
from saltmarket.engine.game import Game, GameResult
from saltmarket.rl import encoding as enc
from saltmarket.rl.agent import AgentStrategy

TableSampler = Callable[[np.random.Generator], list[Strategy]]


class _GameAborted(Exception):
    """Raised on the game thread to stop a game that was abandoned by ``reset``."""


class SaltmarketEnv(gym.Env):
    """One agent seat at a table of opponents chosen by ``sample_table``.

    ``info["action_mask"]`` holds the legal actions. The final reward is 1 for a win and
    0 otherwise. ``shaping`` adds a small potential-based bonus for raising the agent's
    share of table net worth, which does not change which policy is best.
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        sample_table: TableSampler,
        seed: int = 0,
        shaping: float = 0.0,
        gamma: float = 0.999,
        config: GameConfig | None = None,
    ) -> None:
        """Create the env. ``sample_table`` returns the opponents for each new game."""
        self.sample_table = sample_table
        self.shaping = shaping
        self.gamma = gamma
        self.config = config or GameConfig()
        self.observation_space = gym.spaces.Box(-np.inf, np.inf, (enc.OBS_SIZE,), np.float32)
        self.action_space = gym.spaces.Discrete(enc.NUM_ACTIONS)
        self._rng = np.random.default_rng(seed)
        self._to_env: SimpleQueue = SimpleQueue()
        self._to_game: SimpleQueue = SimpleQueue()
        self._thread: threading.Thread | None = None
        self._game: Game | None = None
        self._seat = 0
        self._mask = np.zeros(enc.NUM_ACTIONS, dtype=bool)
        self._potential = 0.0

    def _decide(self, obs: np.ndarray, mask: np.ndarray) -> int:
        self._to_env.put(("decision", obs, mask))
        action = self._to_game.get()
        if action is None:
            raise _GameAborted
        return action

    def _run_game(self, game: Game) -> None:
        try:
            self._to_env.put(("done", game.play()))
        except _GameAborted:
            pass
        except Exception as error:  # noqa: BLE001 - re-raised on the env thread
            self._to_env.put(("error", error))

    def _abort(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            self._to_game.put(None)
            self._thread.join()
        self._thread = None

    def close(self) -> None:
        """Stop any game in progress."""
        self._abort()

    def _table_share(self) -> float:
        state = self._game.state
        worths = [rules.net_worth(state, p.id) for p in state.players]
        total = sum(worths)
        return worths[self._seat] / total if total else 0.0

    def _start_game(self) -> None:
        opponents = self.sample_table(self._rng)
        self._seat = int(self._rng.integers(len(opponents) + 1))
        strategies = list(opponents)
        strategies.insert(self._seat, AgentStrategy(self._decide))
        seed = int(self._rng.integers(2**31))
        self._game = Game(strategies, seed=seed, config=self.config)
        self._thread = threading.Thread(target=self._run_game, args=(self._game,), daemon=True)
        self._thread.start()

    def _info(self, **extra: object) -> dict:
        return {"action_mask": self._mask, **extra}

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        """Start a new game and return the agent's first decision."""
        super().reset(seed=seed)
        if seed is not None:
            self._rng = np.random.default_rng(seed)
        self._abort()
        while True:
            self._start_game()
            message = self._to_env.get()
            if message[0] == "decision":
                _, obs, self._mask = message
                self._potential = self._table_share()
                return obs, self._info()
            if message[0] == "error":
                raise message[1]

    def step(self, action: int):
        """Apply an action and run the game until the agent's next decision or the end."""
        if not self._mask[action]:
            raise ValueError(f"Action {action} is masked out")
        self._to_game.put(int(action))
        message = self._to_env.get()
        if message[0] == "error":
            raise message[1]
        if message[0] == "done":
            return self._finish(message[1])
        _, obs, self._mask = message
        potential = self._table_share()
        reward = self.shaping * (self.gamma * potential - self._potential)
        self._potential = potential
        return obs, reward, False, False, self._info()

    def _finish(self, result: GameResult) -> tuple:
        self._thread.join()
        self._thread = None
        won = result.winner == self._seat
        reward = float(won) - self.shaping * self._potential
        info = self._info(
            won=won, hit_cap=result.hit_cap, table_size=len(result.net_worths), turns=result.turns
        )
        return np.zeros(enc.OBS_SIZE, dtype=np.float32), reward, True, False, info
