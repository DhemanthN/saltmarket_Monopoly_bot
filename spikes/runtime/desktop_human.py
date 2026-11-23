"""Desktop replay of node_human.mjs with the same scripted choices, for comparison."""


import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent / "spike_py"))
from loader import play_human_game  # noqa: E402

count = 0


def decide(obs: np.ndarray, mask: np.ndarray) -> int:
    """Pick a legal action by the same fixed rule node_human.mjs uses."""
    global count
    count += 1
    legal = np.flatnonzero(mask)
    return int(legal[(count * 7) % len(legal)])


print(play_human_game(4242, "cash_hoarder", decide), "decisions", count)
