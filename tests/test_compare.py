import math

import numpy as np
import pandas as pd
import pytest

from saltmarket.analysis.compare import (
    bootstrap_difference,
    learning_curve,
    mcnemar_test,
    stage_win_rates,
    steps_to_reach,
    two_proportion_z_test,
)

pytestmark = pytest.mark.smoke


def test_z_test_matches_a_hand_worked_example():
    # 60/100 against 45/100: pooled rate 0.525, standard error about 0.0706.
    result = two_proportion_z_test(60, 100, 45, 100)
    assert result["difference"] == pytest.approx(0.15)
    assert result["z"] == pytest.approx(2.1239, abs=1e-3)
    assert result["p_value"] == pytest.approx(0.0337, abs=1e-3)


def test_z_test_of_equal_rates_is_not_significant():
    result = two_proportion_z_test(50, 100, 500, 1000)
    assert result["z"] == 0.0
    assert result["p_value"] == pytest.approx(1.0)


def table(rates, games=400):
    return pd.DataFrame(
        {
            "opponent": [f"bot{i}" for i in range(len(rates))],
            "wins": [round(rate * games) for rate in rates],
            "games": games,
        }
    )


def test_bootstrap_interval_covers_the_observed_difference():
    a, b = table([0.9, 0.8, 0.7]), table([0.6, 0.6, 0.6])
    result = bootstrap_difference(a, b, np.random.default_rng(0), replicates=4000)
    assert result["difference"] == pytest.approx(0.2)
    assert result["ci_low"] < 0.2 < result["ci_high"]
    # Each side has 1,200 games, so the interval half-width is about 0.035.
    assert 0.02 < (result["ci_high"] - result["ci_low"]) / 2 < 0.05


def test_bootstrap_is_seeded_and_checks_opponents():
    a, b = table([0.9, 0.5]), table([0.4, 0.5])
    first = bootstrap_difference(a, b, np.random.default_rng(5), replicates=500)
    second = bootstrap_difference(a, b, np.random.default_rng(5), replicates=500)
    assert first == second
    with pytest.raises(ValueError):
        bootstrap_difference(a, table([0.4]), np.random.default_rng(0))


def log():
    return pd.DataFrame(
        {
            "steps": [100, 200, 300, 400],
            "stage": ["random", "random", "full", "full"],
            "episodes": [10, 30, 0, 20],
            "win_rate": [0.0, 1.0, np.nan, 0.5],
        }
    )


def test_learning_curve_pools_games_within_each_bin():
    curve = learning_curve(log(), 200)
    assert curve["steps"].tolist() == [200, 400]
    assert curve["episodes"].tolist() == [40, 20]
    assert curve["win_rate"].tolist() == pytest.approx([0.75, 0.5])
    assert curve["stage"].tolist() == ["random", "full"]


def test_stage_win_rates_weight_by_games():
    rates = stage_win_rates(log())
    assert rates.to_dict() == pytest.approx({"random": 0.75, "full": 0.5})


def test_steps_to_reach_finds_the_first_qualifying_bin():
    curve = learning_curve(log(), 100)
    assert steps_to_reach(curve, 0.5) == 200
    assert steps_to_reach(curve, 0.5, after=200) == 400
    assert steps_to_reach(curve, 0.99, after=200) is None


def test_learning_curve_drops_a_final_partial_bin():
    # The last row ends at 450, so the bin covering 401-600 holds only part of its range.
    partial = pd.concat(
        [log(), pd.DataFrame({"steps": [450], "stage": ["full"], "episodes": [5],
                              "win_rate": [1.0]})],
        ignore_index=True,
    )
    assert learning_curve(partial, 200)["steps"].tolist() == [200, 400]


def test_mcnemar_matches_a_hand_computed_example():
    result = mcnemar_test(30, 10)
    assert result["chi2"] == pytest.approx(19**2 / 40)
    assert result["p_value"] == pytest.approx(math.erfc(math.sqrt(19**2 / 40 / 2)))


def test_mcnemar_is_symmetric_and_handles_no_disagreements():
    assert mcnemar_test(7, 3)["p_value"] == mcnemar_test(3, 7)["p_value"]
    assert mcnemar_test(0, 0)["p_value"] == 1.0
    assert mcnemar_test(5, 5)["p_value"] > 0.7


def test_bootstrap_handles_an_opponent_with_no_games():
    a = pd.DataFrame({"opponent": ["x", "y"], "wins": [3, 0], "games": [4, 0]})
    b = pd.DataFrame({"opponent": ["x", "y"], "wins": [1, 0], "games": [4, 2]})
    result = bootstrap_difference(a, b, np.random.default_rng(0), replicates=200)
    assert result["difference"] == pytest.approx(3 / 4 - 1 / 6)
    assert result["ci_low"] <= result["difference"] <= result["ci_high"]


def test_training_summary_handles_a_run_shorter_than_one_bin():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "scripts" / "compare_agents.py"
    spec = importlib.util.spec_from_file_location("compare_agents", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    log = pd.DataFrame({"steps": [10_000, 20_000], "seconds": [1.0, 2.0],
                        "stage": ["random", "random"], "episodes": [3, 4],
                        "win_rate": [0.5, 0.25]})
    curve = learning_curve(log, module.BIN_STEPS)
    summary = module._training(log, curve)
    assert summary["total_steps"] == 20_000 and summary["final_bin_win_rate"] is None
