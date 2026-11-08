"""Measure simulator speed: single-process games per second and multi-worker scaling.

Usage:
    python scripts/benchmark.py                                # current code only
    python scripts/benchmark.py --baseline-src ../baseline/src  # also time older code
    python scripts/benchmark.py --quick                        # small run, writes nothing

Every measurement is repeated and the median is reported. Single-process timings run
the baseline and the current code back to back in fresh processes, alternating, so both
see the same machine load. Results go to results/benchmark.json and
results/figures/benchmark_scaling.png.

To make a baseline from an older commit, for example ``main``:
    mkdir ../baseline; git archive main src data | tar -x -C ../baseline
"""

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROUND_ROBIN_SEED = 1_000_000_000
TABLE_SEED = 2_000_000_000
TWO_PLAYER_SHARE = 130_000 / 180_000
"""The share of 2-player games in the full tournament, used for the scaling workload."""


def single_process_rate(table_size: int, games: int) -> dict:
    """Play a fixed seeded schedule in this process and return the games per second.

    Only functions that exist in older versions of the engine are used here, so the
    same code can time a baseline checkout.
    """
    from saltmarket.bots.catalog import BOTS
    from saltmarket.sim.tournament import (
        play_matchup,
        random_table_schedule,
        round_robin_schedule,
    )

    bots = sorted(BOTS)
    if table_size == 2:
        schedule = round_robin_schedule(bots, -(-games // 325), ROUND_ROBIN_SEED)[:games]
    else:
        schedule = random_table_schedule(bots, -(-games // table_size), table_size, TABLE_SEED)
        schedule = schedule[:games]
    started = time.perf_counter()
    turns = sum(play_matchup(matchup)[0][0]["turns"] for matchup in schedule)
    seconds = time.perf_counter() - started
    return {"games": len(schedule), "turns": turns, "seconds": seconds,
            "games_per_second": len(schedule) / seconds}


def _time_in_child(src: Path | None, table_size: int, games: int) -> dict:
    """Run ``single_process_rate`` in a fresh interpreter, importing from ``src`` if given."""
    env = dict(os.environ)
    if src is not None:
        env["PYTHONPATH"] = str(src)
    command = [sys.executable, __file__, "--child", str(table_size), str(games)]
    output = subprocess.run(command, env=env, check=True, capture_output=True, text=True)
    return json.loads(output.stdout.strip().splitlines()[-1])


def _median(runs: list[dict], key: str) -> float:
    return statistics.median(run[key] for run in runs)


def benchmark_single(
    sizes: list[int], games: dict[int, int], repeats: int, baseline: Path | None
) -> dict:
    """Time each table size, alternating baseline and current code on every repeat."""
    variants = {"current": None} if baseline is None else {"baseline": baseline, "current": None}
    report = {}
    for size in sizes:
        runs: dict[str, list[dict]] = {name: [] for name in variants}
        for repeat in range(repeats):
            for name, src in variants.items():
                run = _time_in_child(src, size, games[size])
                runs[name].append(run)
                print(f"{size}-player {name} run {repeat + 1}: "
                      f"{run['games_per_second']:.1f} games/s", flush=True)
        entry = {name: {"median_games_per_second": _median(r, "games_per_second"),
                        "runs": r} for name, r in runs.items()}
        if baseline is not None:
            entry["speedup"] = (entry["current"]["median_games_per_second"]
                                / entry["baseline"]["median_games_per_second"])
        report[f"{size}_player"] = entry
    return report


def scaling_schedule(games: int) -> list:
    """Return a mix of 2- and 4-player games in the same proportion as the tournament."""
    from saltmarket.bots.catalog import BOTS
    from saltmarket.sim.tournament import random_table_schedule, round_robin_schedule

    bots = sorted(BOTS)
    two = round(games * TWO_PLAYER_SHARE)
    pairs = round_robin_schedule(bots, -(-two // 325), ROUND_ROBIN_SEED)[:two]
    tables = random_table_schedule(bots, -(-(games - two) // 4), 4, TABLE_SEED)
    return pairs + tables[: games - two]


def worker_counts(maximum: int) -> list[int]:
    """Return 1, 2, 4, ... up to ``maximum``, always ending with ``maximum`` itself."""
    counts = [1]
    while counts[-1] * 2 < maximum:
        counts.append(counts[-1] * 2)
    if counts[-1] != maximum:
        counts.append(maximum)
    return counts


def benchmark_scaling(games: int, counts: list[int], repeats: int, chunk_size: int) -> list[dict]:
    """Time a whole tournament for each worker count, including starting the pool."""
    from saltmarket.sim.tournament import run_tournament

    schedule = scaling_schedule(games)
    times: dict[int, list[float]] = {count: [] for count in counts}
    for repeat in range(repeats):
        for count in counts:
            with tempfile.TemporaryDirectory() as directory:
                started = time.perf_counter()
                run_tournament(schedule, Path(directory), {"kind": "benchmark"}, count,
                               chunk_size, progress=False)
                times[count].append(time.perf_counter() - started)
            rate = games / times[count][-1]
            print(f"{count:>2} workers run {repeat + 1}: {rate:.1f} games/s", flush=True)
    single = games / statistics.median(times[1])
    rows = []
    for count in counts:
        rate = games / statistics.median(times[count])
        rows.append({"workers": count, "median_seconds": statistics.median(times[count]),
                     "seconds": times[count], "games_per_second": rate,
                     "speedup": rate / single, "efficiency": rate / (single * count)})
    return rows


def _mixed_rate(two_player: float, four_player: float) -> float:
    """Return games per second on the tournament mix, from per-table-size rates."""
    seconds_per_game = TWO_PLAYER_SHARE / two_player + (1 - TWO_PLAYER_SHARE) / four_player
    return 1 / seconds_per_game


def summarize(report: dict) -> dict:
    """Return the headline speed-ups computed from a saved report's medians."""
    single = report["single_process"]
    best = max(report["scaling"], key=lambda row: row["games_per_second"])
    summary = {
        "best_workers": best["workers"],
        "best_games_per_second": best["games_per_second"],
        "parallel_speedup": best["speedup"],
        "projected_minutes_for_1m_games": 1_000_000 / best["games_per_second"] / 60,
    }
    if "baseline" in single["2_player"]:
        rates = {name: _mixed_rate(single["2_player"][name]["median_games_per_second"],
                                   single["4_player"][name]["median_games_per_second"])
                 for name in ("baseline", "current")}
        summary.update({
            "baseline_mixed_games_per_second": rates["baseline"],
            "current_mixed_games_per_second": rates["current"],
            "optimization_speedup_mixed": rates["current"] / rates["baseline"],
            "total_speedup_vs_baseline_single_process":
                best["games_per_second"] / rates["baseline"],
            "baseline_single_process_hours_for_1m_games": 1_000_000 / rates["baseline"] / 3600,
        })
    return summary


def main() -> None:
    """Run the benchmarks and save the report and chart."""
    if len(sys.argv) == 4 and sys.argv[1] == "--child":
        print(json.dumps(single_process_rate(int(sys.argv[2]), int(sys.argv[3]))))
        return
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--baseline-src", type=Path, help="src folder of the code to compare")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--games-2p", type=int, default=600)
    parser.add_argument("--games-4p", type=int, default=300)
    parser.add_argument("--scaling-games", type=int, default=6000)
    parser.add_argument("--chunk-size", type=int, default=50)
    parser.add_argument("--max-workers", type=int, default=os.cpu_count() or 1)
    parser.add_argument("--quick", action="store_true", help="tiny run that saves nothing")
    parser.add_argument("--resummarize", action="store_true",
                        help="recompute the summary of results/benchmark.json without timing")
    args = parser.parse_args()
    if args.quick:
        args.repeats, args.games_2p, args.games_4p, args.scaling_games = 1, 40, 20, 200
        args.max_workers = min(args.max_workers, 2)

    import pandas as pd

    from saltmarket.analysis.plots import benchmark_scaling as scaling_chart
    from saltmarket.paths import FIGURES, RESULTS

    if args.resummarize:
        path = RESULTS / "benchmark.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        report["summary"] = summarize(report)
        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report["summary"], indent=2))
        return
    baseline = args.baseline_src.resolve() if args.baseline_src else None
    single = benchmark_single([2, 4], {2: args.games_2p, 4: args.games_4p}, args.repeats,
                              baseline)
    scaling = benchmark_scaling(args.scaling_games, worker_counts(args.max_workers),
                                args.repeats, args.chunk_size)
    best = max(scaling, key=lambda row: row["games_per_second"])
    report = {
        "machine": {"logical_cpus": os.cpu_count(), "platform": platform.platform(),
                    "python": platform.python_version()},
        "settings": {"repeats": args.repeats, "games_2p": args.games_2p,
                     "games_4p": args.games_4p, "scaling_games": args.scaling_games,
                     "scaling_two_player_share": TWO_PLAYER_SHARE,
                     "chunk_size": args.chunk_size, "baseline_src": str(baseline)},
        "note": "Other processes may have been using the CPU. Each value is a median, and "
                "baseline and current runs alternated so they saw the same load.",
        "single_process": single,
        "scaling": scaling,
        "best_workers": best["workers"],
        "projected_seconds_for_1m_games": 1_000_000 / best["games_per_second"],
    }
    report["summary"] = summarize(report)
    print(json.dumps({k: v for k, v in report.items() if k != "single_process"}, indent=2))
    if args.quick:
        return
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    (RESULTS / "benchmark.json").write_text(json.dumps(report, indent=2) + "\n",
                                            encoding="utf-8")
    scaling_chart(pd.DataFrame(scaling), FIGURES / "benchmark_scaling.png")
    print(f"Saved {RESULTS / 'benchmark.json'} and the scaling chart.")


if __name__ == "__main__":
    main()
