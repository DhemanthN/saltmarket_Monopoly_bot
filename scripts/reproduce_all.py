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
    "simulate_all": ["--games-per-pair", "2000", "--tables", "125000"],
    "steps": "20000000",
    "evaluate": ["--games-per-bot", "400", "--tables", "2500"],
    "heldout": ["--games-per-bot", "400"],
    "evaluate_v2": ["--games-per-bot", "1000"],
    "tables_v2": "5000",
    "overlap_seeds": "10",
    "analyze": [],
}
QUICK = {
    "fuzz": ["--games", "100"],
    "bots": ["--games", "10"],
    "landing": ["--games", "20", "--turns", "1000"],
    "simulate": ["--games-per-pair", "2", "--tables", "20"],
    "simulate_all": ["--games-per-pair", "2", "--tables", "20"],
    "steps": "163840",
    "evaluate": ["--games-per-bot", "2", "--tables", "10"],
    "heldout": ["--games-per-bot", "2"],
    "evaluate_v2": ["--games-per-bot", "2"],
    "tables_v2": "10",
    "overlap_seeds": "1",
    "analyze": ["--behavior-games", "26"],
}


def build_steps(settings: dict) -> list[list[str]]:
    """Return every script call in dependency order.

    Version 1 used the 26 training bots. Its tournament and evaluations run first, because
    those evaluations rank the agents against that tournament. The 40-bot tournament and
    the version 2 evaluations, on their own seed set, then replace the tournament tables.
    """
    evaluate = ["evaluate.py", *settings["evaluate"]]
    v2 = ["evaluate.py", "--seed-set", "v2", "--pool", "all", *settings["evaluate_v2"]]
    steps = settings["steps"]
    return [
        ["fuzz.py", *settings["fuzz"]],
        ["fuzz_bots.py", *settings["bots"]],
        ["fuzz_bots.py", *settings["bots"], "--heldout"],
        ["heldout_overlap.py", "--seeds", settings["overlap_seeds"]],
        ["landing_frequency.py", *settings["landing"]],
        ["simulate.py", *settings["simulate"]],
        ["train.py", "--steps", steps, "--run", "main"],
        ["train.py", "--steps", steps, "--run", "two_player", "--opponents", "1"],
        ["train_dqn.py", "--steps", steps, "--run", "dqn_two_player"],
        [*evaluate, "--run", "main"],
        [*evaluate, "--run", "main", "--seed-set", "fresh"],
        [*evaluate, "--run", "two_player"],
        [*evaluate, "--run", "two_player", "--seed-set", "fresh"],
        [*evaluate, "--run", "dqn_two_player", "--seed-set", "fresh", "--label", "dqn"],
        ["evaluate_heldout.py", "--run", "two_player", *settings["heldout"]],
        ["simulate.py", "--pool", "all", *settings["simulate_all"]],
        [*v2, "--run", "two_player", "--tables", "0"],
        [*v2, "--run", "dqn_two_player", "--tables", "0", "--label", "dqn"],
        [*v2, "--run", "main", "--tables", settings["tables_v2"]],
        ["compare_agents.py", "--suffix", "v2_all"],
        ["project_stats.py"],
        [
            "analyze.py", "--runs", "main", "two_player", "--best-run", "two_player",
            "--suffix", "_v2_all", "--raw-suffix", "_all", "--dqn-run", "dqn_two_player",
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
