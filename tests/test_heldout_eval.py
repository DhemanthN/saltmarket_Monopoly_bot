import importlib.util
from pathlib import Path

import pandas as pd
import pytest

from saltmarket.bots.catalog import BOTS
from saltmarket.bots.heldout.catalog import HELDOUT_BOTS
from saltmarket.bots.registry import ALL_NAMED_BOTS
from saltmarket.rl import evaluate as ev

smoke = pytest.mark.smoke


@smoke
def test_heldout_seed_range_is_separate_from_other_evaluations():
    heldout = ev.two_player_schedule(sorted(HELDOUT_BOTS), 400, ev.HELDOUT_SEED_OFFSET)
    fresh = ev.two_player_schedule(sorted(BOTS), 400, ev.FRESH_SEED_OFFSET)
    default = ev.two_player_schedule(sorted(BOTS), 400)
    seeds = {g.seed for g in heldout}
    assert not seeds & {g.seed for g in fresh} and not seeds & {g.seed for g in default}
    assert min(seeds) >= 2**31


@smoke
def test_a_bot_can_take_the_agent_seat_and_be_paired():
    schedule = ev.two_player_schedule(["cash_reader", "finisher"], 2, ev.HELDOUT_SEED_OFFSET)
    first = pd.DataFrame(ev.play_eval_games(schedule, None, True, subject="auction_sniper"))
    second = pd.DataFrame(ev.play_eval_games(schedule, None, True, subject="never_buy"))
    assert list(first["seat"]) == [0, 0, 1, 1]
    assert first["won"].sum() >= second["won"].sum()
    paired = ev.paired_outcomes(first, second)
    assert paired["games"] == 4
    assert sum(v for k, v in paired.items() if k != "games") == 4


@smoke
def test_v2_seed_set_is_separate_from_every_earlier_evaluation():
    pool = sorted(ALL_NAMED_BOTS)
    v2 = ev.two_player_schedule(pool, 1000, ev.V2_SEED_OFFSET)
    v2 += ev.four_player_schedule(pool, 2500, ev.V2_SEED_OFFSET)
    earlier = set()
    for offset in (0, ev.FRESH_SEED_OFFSET, ev.HELDOUT_SEED_OFFSET):
        earlier |= {g.seed for g in ev.two_player_schedule(pool, 1000, offset)}
        earlier |= {g.seed for g in ev.four_player_schedule(pool, 2500, offset)}
    seeds = {g.seed for g in v2}
    assert len(seeds) == len(v2) and not seeds & earlier and min(seeds) >= 2**31


def _evaluate_script():
    path = Path(__file__).resolve().parents[1] / "scripts" / "evaluate.py"
    spec = importlib.util.spec_from_file_location("evaluate_script", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@smoke
def test_evaluation_outputs_are_named_by_seed_set_and_pool():
    script = _evaluate_script()
    assert script.output_suffix("two_player", False, "fresh", "training") == "two_player_fresh"
    assert script.output_suffix("main", False, "default", "training") == "main"
    assert script.output_suffix("dqn", True, "v2", "all") == "dqn_sampled_v2_all"


@smoke
def test_pool_summaries_split_training_and_heldout_opponents():
    script = _evaluate_script()
    frame = pd.DataFrame(
        {
            "opponents": ["balanced", "balanced", "finisher", "finisher"],
            "won": [1, 0, 1, 1],
            "hit_cap": [0, 0, 0, 1],
        }
    )
    split = script.pool_summaries(frame)
    assert split["training"]["games"] == 2 and split["training"]["wins"] == 1
    assert split["heldout"]["games"] == 2 and split["heldout"]["wins"] == 2


@smoke
def test_heldout_split_pools_close_variants_separately():
    path = Path(__file__).resolve().parents[1] / "scripts" / "analyze.py"
    spec = importlib.util.spec_from_file_location("analyze_script", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    overlap = pd.DataFrame({"heldout_bot": ["cash_reader", "finisher", "phase_shifter"],
                            "identical_share": [0.7, 0.02, 0.0]})
    table = pd.DataFrame({"opponent": ["balanced", "cash_reader", "finisher", "phase_shifter"],
                          "wins": [9, 8, 6, 4], "games": [10, 10, 10, 10]})
    split = module.heldout_split({"ppo": table}, overlap).set_index("group")
    assert split.loc["close_variant", "wins"] == 8 and split.loc["close_variant", "bots"] == 1
    assert split.loc["distinct", "wins"] == 10 and split.loc["distinct", "games"] == 20
