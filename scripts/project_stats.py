"""Count what the project has simulated and built, from saved results and the source tree.

Usage: python scripts/project_stats.py
Reads results/*.json, results/*.csv, and the training logs, counts Python lines and
collected tests, and writes results/project_stats.json. Run it after every other script,
so the totals cover the latest results.
"""

import json
import re
import subprocess
import sys

import pandas as pd

from saltmarket.paths import RESULTS, ROOT

CODE_FOLDERS = ("src", "scripts", "tests")


def tournament_totals() -> dict:
    """Return games and turns in the latest saved tournament, by table size."""
    summary = json.loads((RESULTS / "tournament_summary.json").read_text())
    sizes = {name: summary[name] for name in ("two_player", "four_player")}
    return {
        "pool": summary.get("pool", "training"),
        "bots": summary["bots"],
        "games": sum(part["games"] for part in sizes.values()),
        "turns": sum(part["total_turns"] for part in sizes.values()),
        "by_table_size": {
            name: {"games": part["games"], "turns": part["total_turns"]}
            for name, part in sizes.items()
        },
    }


def evaluation_games() -> dict[str, int]:
    """Return the games played in each saved agent evaluation file."""
    counts = {}
    for path in sorted(RESULTS.glob("rl_eval_summary_*.json")):
        summary = json.loads(path.read_text())
        counts[path.name] = sum(
            summary[size]["games"] for size in ("two_player", "four_player") if size in summary
        )
    heldout = RESULTS / "rl_eval_heldout_bots.json"
    if heldout.exists():
        summary = json.loads(heldout.read_text())
        counts[heldout.name] = summary["agent"]["games"] + summary["baseline_result"]["games"]
    return counts


def fuzz_totals() -> dict:
    """Return games and turns in the rules fuzz test and both bot fuzz tests."""
    rules = json.loads((RESULTS / "fuzz_summary.json").read_text())
    bots = pd.concat(
        [pd.read_csv(RESULTS / name) for name in ("bot_fuzz.csv", "bot_fuzz_heldout.csv")
         if (RESULTS / name).exists()]
    )
    return {
        "games": int(rules["games"] + bots["games"].sum()),
        "turns": int(rules["total_turns"] + bots["turns"].sum()),
    }


def training_games() -> dict[str, int]:
    """Return the games finished during each logged training run."""
    return {
        path.name: int(pd.read_csv(path)["episodes"].sum())
        for path in sorted(RESULTS.glob("training_log_*.csv"))
    }


def python_lines() -> dict[str, int]:
    """Count non-blank lines in the project's Python files, by folder."""
    counts = {}
    for folder in CODE_FOLDERS:
        files = (ROOT / folder).rglob("*.py")
        counts[folder] = sum(
            sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
            for path in files
        )
    return counts


def collected_tests() -> int:
    """Return how many tests pytest collects, slow ones included."""
    output = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    return int(re.search(r"(\d+) tests? collected", output).group(1))


def main() -> None:
    """Write results/project_stats.json and print it."""
    tournament = tournament_totals()
    evaluations = evaluation_games()
    fuzz = fuzz_totals()
    training = training_games()
    lines = python_lines()
    stats = {
        "tournament": tournament,
        "evaluation_games": {"total": sum(evaluations.values()), "by_file": evaluations},
        "fuzz": fuzz,
        "training_games": {"total": sum(training.values()), "by_log": training},
        "games_simulated_total": tournament["games"] + sum(evaluations.values())
        + fuzz["games"] + sum(training.values()),
        "turns_in_tournament_and_fuzz": tournament["turns"] + fuzz["turns"],
        "python_lines_non_blank": {"total": sum(lines.values()), **lines},
        "tests_collected": collected_tests(),
        "note": "Games simulated counts the latest tournament, every saved evaluation, the "
                "fuzz tests, and games finished in training. Turns are counted only where "
                "results save them: the tournament and the fuzz tests.",
    }
    (RESULTS / "project_stats.json").write_text(json.dumps(stats, indent=2) + "\n")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
