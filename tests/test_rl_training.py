from collections import Counter

import numpy as np
import pandas as pd
import pytest

from saltmarket.bots.catalog import BOTS
from saltmarket.rl import encoding as enc
from saltmarket.rl import evaluate as ev
from saltmarket.rl.policy import NumpyPolicy
from saltmarket.rl.ppo import ActorCritic, PPOConfig
from saltmarket.rl.train import (
    CURRICULUM,
    TrainConfig,
    load_policy,
    save_policy,
    stage_at,
    train,
)
from saltmarket.rl.workers import TableSpec, sample_opponents, snapshot_bot

smoke = pytest.mark.smoke
POOL = ["always_buy", "balanced", "expert", "random"]


def weights():
    return ActorCritic(enc.OBS_SIZE, enc.NUM_ACTIONS, 8).numpy_weights()


@smoke
@pytest.mark.parametrize(
    ("fraction", "name"),
    [(0.0, "random"), (0.1, "simple"), (0.5, "full"), (0.9, "self_play")],
)
def test_curriculum_stages(fraction, name):
    assert stage_at(fraction).name == name


@smoke
def test_curriculum_ends_with_the_full_pool_and_self_play():
    assert set(CURRICULUM[-1].pool) == set(BOTS)
    assert CURRICULUM[-1].snapshot_share > 0


@smoke
def test_sample_opponents_gives_two_and_four_player_tables():
    rng = np.random.default_rng(0)
    sizes = Counter(len(sample_opponents(TableSpec(POOL), rng)) + 1 for _ in range(100))
    assert set(sizes) == {2, 4}


@smoke
def test_snapshots_are_used_only_when_available():
    rng = np.random.default_rng(0)
    spec = TableSpec(["random"], [weights()], 1.0)
    assert all(bot.name == "ppo" for bot in sample_opponents(spec, rng))
    spec = TableSpec(["random"], [], 1.0)
    assert all(bot.name == "random" for bot in sample_opponents(spec, rng))


@smoke
def test_snapshot_bot_picks_legal_actions():
    bot = snapshot_bot(weights(), np.random.default_rng(0))
    obs = np.zeros(enc.OBS_SIZE, dtype=np.float32)
    mask = np.zeros(enc.NUM_ACTIONS, dtype=bool)
    mask[[enc.PASS, enc.YES]] = True
    assert bot.decide(obs, mask) in (enc.PASS, enc.YES)


@smoke
def test_policy_save_and_load_round_trip(tmp_path):
    original = weights()
    path = tmp_path / "policy.npz"
    save_policy(original, path)
    loaded = load_policy(path)
    obs = np.ones(enc.OBS_SIZE, dtype=np.float32)
    assert NumpyPolicy(original).value(obs) == pytest.approx(NumpyPolicy(loaded).value(obs))


@smoke
def test_two_player_schedule_balances_seats_and_opponents():
    schedule = ev.two_player_schedule(POOL, 4)
    assert len(schedule) == 16
    assert all(ev.AGENT in game.seats for game in schedule)
    assert Counter(game.seats.index(ev.AGENT) for game in schedule) == {0: 8, 1: 8}


@smoke
def test_four_player_schedule_rotates_agent_through_every_seat():
    schedule = ev.four_player_schedule(POOL, 3)
    assert len(schedule) == 12
    assert sorted(game.seats.index(ev.AGENT) for game in schedule[:4]) == [0, 1, 2, 3]
    assert all(len(set(game.seats)) == 4 for game in schedule)


@smoke
def test_evaluation_seeds_are_unique_and_outside_the_training_range():
    games = ev.two_player_schedule(POOL, 3) + ev.four_player_schedule(POOL, 3)
    seeds = [game.seed for game in games]
    assert len(set(seeds)) == len(seeds)
    assert min(seeds) >= ev.EVAL_SEED_BASE > 2**31


@smoke
def test_play_eval_games_is_deterministic():
    games = ev.two_player_schedule(["balanced"], 2)
    policy = weights()
    first = ev.play_eval_games(games, policy, greedy=True)
    assert first == ev.play_eval_games(games, policy, greedy=True)
    assert first[0]["opponents"] == "balanced"


@smoke
def test_summaries_report_all_and_decided_games():
    frame = pd.DataFrame(
        {"won": [1, 1, 0, 0], "hit_cap": [1, 1, 0, 0], "opponents": ["a", "a", "a|b", "b"]}
    )
    summary = ev.summarize_wins(frame)
    assert summary["win_rate"] == 0.5 and summary["decided_win_rate"] == 0.0
    table = ev.per_opponent(frame).set_index("opponent")
    assert table.loc["a", "games"] == 3 and table.loc["b", "games"] == 2


@pytest.mark.slow
def test_training_runs_logs_and_resumes(tmp_path):
    ppo_config = PPOConfig(hidden_size=16, minibatch_size=128, epochs=1)
    config = TrainConfig(
        total_steps=512, workers=2, steps_per_worker=128, device="cpu", checkpoint_every=1
    )
    log = tmp_path / "log.csv"
    train(config, ppo_config, tmp_path / "run", log)
    assert len(pd.read_csv(log)) == 2
    longer = TrainConfig(
        total_steps=1024, workers=2, steps_per_worker=128, device="cpu", checkpoint_every=1
    )
    train(longer, ppo_config, tmp_path / "run", log)
    assert pd.read_csv(log)["update"].tolist() == [1, 2, 3, 4]
