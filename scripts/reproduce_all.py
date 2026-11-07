"""Reproduce every result and chart with one command.

Usage: python scripts/reproduce_all.py          full run, estimated at over an hour
       python scripts/reproduce_all.py --quick  small check, about 3 minutes

--quick writes to quick_output/ so it never touches the real results. Its numbers are far
too small to mean anything. It only proves that the whole pipeline runs from start to end.

Simulations and evaluations repeat exactly for a given seed. Training runs across parallel
processes and a GPU, so a retrained agent should land close to the saved one, not match it
bit for bit.
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUICK_OUTPUT = ROOT / "quick_output"

FULL = {
    "fuzz": ["--games", "10000"],
    "bots": ["--games", "1000"],
    "landing": ["--games", "400", "--turns", "4000"],
    "simulate": ["--games-per-pair", "400", "--tables", "12500"],
    "steps": "20000000",
    "evaluate": ["--games-per-bot", "400", "--tables", "2500"],
    "analyze": [],
}
QUICK = {
    "fuzz": ["--games", "100"],
    "bots": ["--games", "10"],
    "landing": ["--games", "20", "--turns", "1000"],
    "simulate": ["--games-per-pair", "2", "--tables", "20"],
    "steps": "163840",
    "evaluate": ["--games-per-bot", "2", "--tables", "10"],
    "analyze": ["--behavior-games", "26"],
}


def build_steps(settings: dict) -> list[list[str]]:
    """Return every script call in dependency order."""
    evaluate = ["evaluate.py", *settings["evaluate"]]
    steps = settings["steps"]
    return [
        ["fuzz.py", *settings["fuzz"]],
        ["fuzz_bots.py", *settings["bots"]],
        ["landing_frequency.py", *settings["landing"]],
        ["simulate.py", *settings["simulate"]],
        ["train.py", "--steps", steps, "--run", "main"],
        ["train.py", "--steps", steps, "--run", "two_player", "--opponents", "1"],
        [*evaluate, "--run", "main"],
        [*evaluate, "--run", "main", "--fresh-seeds"],
        [*evaluate, "--run", "two_player"],
        [*evaluate, "--run", "two_player", "--fresh-seeds"],
        [
            "analyze.py", "--runs", "main", "two_player", "--best-run", "two_player", "--fresh",
            *settings["analyze"],
        ],
    ]


def main() -> None:
    """Run each step, stopping at the first failure."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()

    env = dict(os.environ)
    if args.quick:
        env["SALTMARKET_OUTPUT"] = str(QUICK_OUTPUT)
    started = time.perf_counter()
    for step in build_steps(QUICK if args.quick else FULL):
        print(f"\n=== {' '.join(step)} ===", flush=True)
        subprocess.run([sys.executable, str(ROOT / "scripts" / step[0]), *step[1:]], env=env,
                       check=True, stdout=subprocess.DEVNULL)
    print(f"\nFinished in {(time.perf_counter() - started) / 60:.1f} minutes")


if __name__ == "__main__":
    main()
