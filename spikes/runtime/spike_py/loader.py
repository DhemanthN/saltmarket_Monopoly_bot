"""Python that runs inside Pyodide (and on desktop) for the runtime spike.

Torch-free copy of ``load_policy`` plus helpers the JavaScript harness calls.
"""

import json
from collections.abc import Callable

import numpy as np

from saltmarket.bots.catalog import BOTS
from saltmarket.bots.registry import make_any_bot
from saltmarket.engine.game import Game
from saltmarket.rl.agent import AgentStrategy
from saltmarket.rl.policy import NumpyPolicy, PolicyWeights
from saltmarket.sim.fingerprint import fingerprint_schedule, game_fingerprint


def load_weights(path: str) -> PolicyWeights:
    """Read ``actor_i_w/b`` and ``critic_i_w/b`` arrays like ``rl.train.load_policy``."""
    with np.load(path) as data:
        def layers(name: str) -> tuple:
            count = sum(key.startswith(name) and key.endswith("_w") for key in data.files)
            return tuple((data[f"{name}_{i}_w"], data[f"{name}_{i}_b"]) for i in range(count))

        return PolicyWeights(layers("actor"), layers("critic"))


def fingerprints(table_size: int, games: int) -> str:
    """Return JSON fingerprints for the first ``games`` of the golden schedule."""
    schedule = fingerprint_schedule(sorted(BOTS), games, table_size)
    return json.dumps([game_fingerprint(m) for m in schedule])


def policy_check(model_path: str, fixture_path: str, name: str) -> str:
    """Compare ``NumpyPolicy.greedy`` here with the desktop actions saved in the fixture."""
    from saltmarket.rl.policy import MASKED_LOGIT, _forward

    with np.load(fixture_path) as data:
        obs, masks = data["obs"], data["masks"]
        expected, logits = data[f"{name}_actions"], data[f"{name}_logits"]
    weights = load_weights(model_path)
    policy = NumpyPolicy(weights)
    actions = [policy.greedy(o, m) for o, m in zip(obs, masks, strict=True)]
    pairs = list(zip(obs, masks, strict=True))
    mine = np.array([np.where(m, _forward(weights.actor, o), MASKED_LOGIT) for o, m in pairs])
    return json.dumps({
        "matches": int(sum(a == int(e) for a, e in zip(actions, expected, strict=False))),
        "total": len(actions),
        "max_logit_diff": float(np.abs(mine - logits).max()),
    })


def play_human_game(
    seed: int, bot: str, human_decide: Callable[[np.ndarray, np.ndarray], int]
) -> str:
    """Play seat 0 as a blocking human seat against ``bot``. Return JSON summary and hash."""
    seats = [AgentStrategy(human_decide), make_any_bot(bot)]
    game = Game(seats, seed=seed, record_log=True)
    result = game.play()
    return json.dumps(
        {"winner": result.winner, "turns": result.turns, "events": len(game.log or ())}
    )
