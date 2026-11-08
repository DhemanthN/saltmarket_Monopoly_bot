import pandas as pd
import pytest

from saltmarket.bots.catalog import BOTS
from saltmarket.bots.heldout.catalog import HELDOUT_BOTS
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
