import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.smoke

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "benchmark.py"
spec = importlib.util.spec_from_file_location("benchmark", SCRIPT)
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


@pytest.mark.parametrize(
    ("maximum", "expected"),
    [(1, [1]), (2, [1, 2]), (8, [1, 2, 4, 8]), (24, [1, 2, 4, 8, 16, 24])],
)
def test_worker_counts_double_and_end_at_the_maximum(maximum, expected):
    assert benchmark.worker_counts(maximum) == expected


def test_scaling_schedule_matches_the_tournament_mix():
    schedule = benchmark.scaling_schedule(360)
    two = sum(len(m.names) == 2 for m in schedule)
    assert len(schedule) == 360
    assert two == round(360 * benchmark.TWO_PLAYER_SHARE)
    assert len({m.seed for m in schedule if len(m.names) == 2}) == two


def test_summary_combines_measured_medians():
    def single(rate):
        return {"median_games_per_second": rate}

    report = {
        "single_process": {
            "2_player": {"baseline": single(10.0), "current": single(20.0)},
            "4_player": {"baseline": single(10.0), "current": single(20.0)},
        },
        "scaling": [
            {"workers": 1, "games_per_second": 20.0, "speedup": 1.0},
            {"workers": 4, "games_per_second": 60.0, "speedup": 3.0},
        ],
    }
    summary = benchmark.summarize(report)
    assert summary["best_workers"] == 4
    assert summary["optimization_speedup_mixed"] == pytest.approx(2.0)
    assert summary["total_speedup_vs_baseline_single_process"] == pytest.approx(6.0)
    assert summary["projected_minutes_for_1m_games"] == pytest.approx(1e6 / 60 / 60)


def test_single_process_rate_plays_the_requested_games():
    result = benchmark.single_process_rate(4, 3)
    assert result["games"] == 3
    assert result["games_per_second"] > 0
