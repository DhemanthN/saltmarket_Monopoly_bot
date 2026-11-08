import gymnasium as gym
import numpy as np
import pandas as pd
import pytest
import torch

from saltmarket.bots.catalog import make_bot
from saltmarket.rl import encoding as enc
from saltmarket.rl.dqn import (
    DQN,
    DQNConfig,
    DuelingQNetwork,
    ReplayBuffer,
    double_dqn_targets,
    masked_q_values,
)
from saltmarket.rl.dqn_train import DQNTrainConfig, epsilon_at, train_dqn, updates_for
from saltmarket.rl.dqn_workers import (
    TransitionCollector,
    Transitions,
    epsilon_greedy,
    merge_transitions,
    q_snapshot_bot,
)
from saltmarket.rl.env import SaltmarketEnv
from saltmarket.rl.policy import NumpyPolicy, PolicyWeights
from saltmarket.rl.workers import TableSpec, sample_opponents

smoke = pytest.mark.smoke
INF = float("inf")


def transitions(count, obs_size=3, actions=4, start=0):
    ids = np.arange(start, start + count, dtype=np.float32)
    return Transitions(
        obs=np.repeat(ids[:, None], obs_size, axis=1),
        masks=np.ones((count, actions), dtype=bool),
        actions=np.arange(start, start + count) % actions,
        rewards=ids,
        discounts=np.full(count, 0.9, dtype=np.float32),
        next_obs=np.repeat(ids[:, None] + 1, obs_size, axis=1),
        next_masks=np.ones((count, actions), dtype=bool),
    )


# Replay buffer


@smoke
def test_buffer_stores_and_samples_whole_transitions():
    buffer = ReplayBuffer(10, 3, 4)
    buffer.add(transitions(6))
    assert len(buffer) == 6
    sample = buffer.sample(50, np.random.default_rng(0))
    assert sample.obs.shape == (50, 3)
    assert set(sample.rewards) <= set(range(6))
    # Every field of a sampled row comes from the same stored transition.
    assert np.array_equal(sample.obs[:, 0], sample.rewards)
    assert np.array_equal(sample.next_obs[:, 0], sample.rewards + 1)
    assert np.array_equal(sample.actions, sample.rewards.astype(int) % 4)


@smoke
def test_buffer_overwrites_the_oldest_when_full():
    buffer = ReplayBuffer(5, 3, 4)
    buffer.add(transitions(4))
    buffer.add(transitions(3, start=4))
    assert len(buffer) == 5
    assert sorted(buffer.rewards) == [2, 3, 4, 5, 6]
    assert buffer.position == 2


@smoke
def test_buffer_keeps_only_the_newest_of_an_oversized_batch():
    buffer = ReplayBuffer(4, 3, 4)
    buffer.add(transitions(9))
    assert sorted(buffer.rewards) == [5, 6, 7, 8]


@smoke
def test_buffer_sampling_is_seeded_and_refuses_when_empty():
    buffer = ReplayBuffer(8, 3, 4)
    with pytest.raises(ValueError):
        buffer.sample(1, np.random.default_rng(0))
    buffer.add(transitions(8))
    first = buffer.sample(16, np.random.default_rng(3)).rewards
    second = buffer.sample(16, np.random.default_rng(3)).rewards
    assert np.array_equal(first, second)


@smoke
def test_buffer_state_round_trip():
    buffer = ReplayBuffer(5, 3, 4)
    buffer.add(transitions(7))
    restored = ReplayBuffer(5, 3, 4)
    restored.load_state_dict(buffer.state_dict())
    assert (restored.size, restored.position) == (buffer.size, buffer.position)
    assert np.array_equal(restored.rewards, buffer.rewards)
    assert np.array_equal(restored.next_masks, buffer.next_masks)


@smoke
def test_merge_transitions_concatenates_every_field():
    merged = merge_transitions([transitions(2), transitions(3, start=2)])
    assert len(merged) == 5
    assert merged.rewards.tolist() == [0, 1, 2, 3, 4]


# Masked targets


@smoke
def test_masked_q_values_are_minus_infinity_for_illegal_actions():
    q = torch.tensor([[1.0, 5.0, 2.0]])
    masked = masked_q_values(q, torch.tensor([[True, False, True]]))
    assert masked.tolist() == [[1.0, -INF, 2.0]]


@smoke
def test_target_ignores_illegal_actions_even_with_the_highest_q():
    masks = torch.tensor([[True, False, True]])
    online = masked_q_values(torch.tensor([[1.0, 99.0, 3.0]]), masks)
    target = masked_q_values(torch.tensor([[10.0, 50.0, 2.0]]), masks)
    result = double_dqn_targets(online, target, torch.tensor([1.0]), torch.tensor([0.5]))
    # The online net picks action 2 (best legal), and the target net scores it at 2.0.
    assert result.item() == pytest.approx(1.0 + 0.5 * 2.0)


@smoke
def test_double_dqn_scores_the_online_choice_with_the_target_net():
    masks = torch.ones(1, 3, dtype=bool)
    online = torch.tensor([[0.0, 1.0, 0.5]])
    target = torch.tensor([[7.0, 2.0, 9.0]])
    result = double_dqn_targets(online, target, torch.tensor([0.0]), torch.tensor([1.0]))
    # A plain max over the target net would give 9. Double DQN uses action 1 instead.
    assert result.item() == pytest.approx(2.0)
    assert masks.all()


@smoke
def test_finished_games_target_only_the_reward_without_nans():
    no_moves = torch.zeros(2, 3, dtype=bool)
    online = masked_q_values(torch.randn(2, 3), no_moves)
    target = masked_q_values(torch.randn(2, 3), no_moves)
    result = double_dqn_targets(online, target, torch.tensor([1.0, 0.0]), torch.zeros(2))
    assert result.tolist() == [1.0, 0.0]


# Dueling head


@smoke
def test_dueling_q_values_average_to_the_state_value_over_legal_actions():
    torch.manual_seed(0)
    network = DuelingQNetwork(5, 6, 16)
    obs = torch.randn(4, 5)
    masks = torch.tensor([[True, True, False, True, False, True]] * 4)
    q = network(obs, masks)
    assert torch.isinf(q[~masks]).all()
    value = network.value(network.trunk(obs)).squeeze(-1)
    assert torch.allclose(q[masks].view(4, 4).mean(-1), value, atol=1e-6)


@smoke
def test_fresh_network_starts_with_q_values_near_zero():
    # A large starting value has to be unlearned one bootstrap hop at a time, which
    # stalled the first full training run (see docs/rl.md).
    torch.manual_seed(0)
    network = DuelingQNetwork(enc.OBS_SIZE, enc.NUM_ACTIONS, 256)
    obs = torch.rand(512, enc.OBS_SIZE)
    with torch.no_grad():
        q = network(obs, torch.ones(512, enc.NUM_ACTIONS, dtype=bool))
    assert q.abs().max() < 0.1


@smoke
def test_target_refresh_is_frequent_relative_to_a_game():
    # About 128 decisions are collected per gradient step at the default replay ratio,
    # so a refresh every 250 steps is about 32,000 decisions, near 100 games.
    assert DQNConfig().target_update_every <= 250


@smoke
def test_dueling_gradients_reach_both_heads():
    network = DuelingQNetwork(5, 6, 16)
    q = network(torch.randn(3, 5), torch.ones(3, 6, dtype=bool))
    q[:, 0].sum().backward()
    assert network.value.weight.grad.abs().sum() > 0
    assert network.advantage.weight.grad.abs().sum() > 0


@smoke
def test_numpy_export_picks_the_same_action_as_torch():
    torch.manual_seed(1)
    network = DuelingQNetwork(enc.OBS_SIZE, enc.NUM_ACTIONS, 32)
    policy = NumpyPolicy(network.numpy_weights())
    rng = np.random.default_rng(0)
    for _ in range(20):
        obs = rng.normal(size=enc.OBS_SIZE).astype(np.float32)
        mask = rng.random(enc.NUM_ACTIONS) < 0.3
        mask[rng.integers(enc.NUM_ACTIONS)] = True
        q = network(torch.as_tensor(obs)[None], torch.as_tensor(mask)[None])
        assert policy.greedy(obs, mask) == int(q.argmax())
        expected = network.value(network.trunk(torch.as_tensor(obs))).item()
        assert policy.value(obs) == pytest.approx(expected, abs=1e-5)


# Learner


def bandit_batch(size=64):
    actions = np.array([0, 1] * (size // 2))
    return Transitions(
        np.ones((size, 2), np.float32), np.ones((size, 2), bool), actions,
        np.where(actions == 1, 1.0, 0.0).astype(np.float32), np.zeros(size, np.float32),
        np.zeros((size, 2), np.float32), np.zeros((size, 2), bool),
    )


def test_update_learns_the_rewarded_action():
    config = DQNConfig(hidden_size=16, learning_rate=0.01, target_update_every=10)
    dqn = DQN(2, 2, config, seed=0)
    for _ in range(200):
        dqn.update(bandit_batch())
    with torch.no_grad():
        q = dqn.online(torch.ones(1, 2), torch.ones(1, 2, dtype=bool))[0].tolist()
    assert q[1] == pytest.approx(1.0, abs=0.1)
    assert q[0] == pytest.approx(0.0, abs=0.1)


@smoke
def test_target_network_syncs_on_schedule():
    dqn = DQN(2, 2, DQNConfig(hidden_size=8, learning_rate=0.1, target_update_every=3), seed=0)
    start = dqn.target.advantage.weight.clone()
    for _ in range(2):
        dqn.update(bandit_batch())
    assert torch.equal(dqn.target.advantage.weight, start)
    dqn.update(bandit_batch())
    assert torch.equal(dqn.target.advantage.weight, dqn.online.advantage.weight)


# Collection


class CountingEnv(gym.Env):
    """Rewards 1, 2, 3, ... and ends after ``length`` steps, by termination or truncation."""

    def __init__(self, length=5, truncate=False):
        self.length, self.truncate = length, truncate
        self.observation_space = gym.spaces.Box(-np.inf, np.inf, (1,), np.float32)
        self.action_space = gym.spaces.Discrete(2)
        self.t = 0

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.t = 0
        return np.array([0.0], np.float32), {}

    def step(self, action):
        self.t += 1
        end = self.t == self.length
        obs = np.array([self.t], np.float32)
        return obs, float(self.t), end and not self.truncate, end and self.truncate, {}


def zero_policy(obs_size=1, actions=2):
    layers = ((np.zeros((obs_size, actions)), np.zeros(actions)),)
    return NumpyPolicy(PolicyWeights(layers, layers))


@smoke
def test_n_step_rewards_and_discounts_on_a_terminating_game():
    collector = TransitionCollector(CountingEnv(5), 0, 2, gamma=0.5, n_step=2)
    batch = collector.collect(zero_policy(), 5, epsilon=0.0).transitions
    assert batch.obs[:, 0].tolist() == [0, 1, 2, 3, 4]
    assert batch.rewards.tolist() == pytest.approx([2.0, 3.5, 5.0, 6.5, 5.0])
    assert batch.discounts.tolist() == [0.25, 0.25, 0.25, 0.0, 0.0]
    assert batch.next_obs[:3, 0].tolist() == [2, 3, 4]
    assert not batch.next_masks[3:].any()


@smoke
def test_truncated_game_still_bootstraps_from_its_last_state():
    collector = TransitionCollector(CountingEnv(3, truncate=True), 0, 2, gamma=0.5, n_step=4)
    experience = collector.collect(zero_policy(), 3, epsilon=0.0)
    batch = experience.transitions
    assert batch.discounts.tolist() == [0.125, 0.25, 0.5]
    assert batch.next_obs[:, 0].tolist() == [3, 3, 3]
    assert batch.next_masks.all()
    assert experience.episode_returns == [6.0]


@smoke
def test_pending_steps_carry_over_between_calls():
    collector = TransitionCollector(CountingEnv(10), 0, 2, gamma=0.9, n_step=4)
    first = collector.collect(zero_policy(), 3, epsilon=0.0).transitions
    second = collector.collect(zero_policy(), 3, epsilon=0.0).transitions
    assert len(first) == 0
    assert second.obs[:, 0].tolist() == [0, 1, 2]


@smoke
def test_epsilon_greedy_respects_the_mask():
    rng = np.random.default_rng(0)
    policy = zero_policy(1, 5)
    mask = np.array([False, True, False, True, False])
    obs = np.zeros(1, np.float32)
    assert {epsilon_greedy(policy, obs, mask, 1.0, rng) for _ in range(200)} == {1, 3}
    assert epsilon_greedy(policy, obs, mask, 0.0, rng) == policy.greedy(obs, mask)


def test_saltmarket_collection_only_takes_legal_actions():
    env = SaltmarketEnv(lambda rng: [make_bot("never_buy")], seed=3, shaping=0.2)
    network = DuelingQNetwork(enc.OBS_SIZE, enc.NUM_ACTIONS, 16)
    collector = TransitionCollector(env, 3, enc.NUM_ACTIONS, gamma=0.999, n_step=8)
    experience = collector.collect(NumpyPolicy(network.numpy_weights()), 4000, epsilon=0.5)
    env.close()
    batch = experience.transitions
    assert batch.masks[np.arange(len(batch)), batch.actions].all()
    assert experience.episode_infos, "expected at least one finished game"
    ended = batch.discounts == 0
    assert ended.any() and not batch.next_masks[ended].any()
    assert batch.next_masks[~ended].any(axis=1).all()


@smoke
def test_q_snapshot_bot_is_used_for_dqn_self_play():
    network = DuelingQNetwork(enc.OBS_SIZE, enc.NUM_ACTIONS, 8)
    spec = TableSpec(["random"], [network.numpy_weights()], 1.0, (1,))
    calls = []

    def factory(weights, rng):
        calls.append(weights)
        return q_snapshot_bot(weights, rng)

    opponents = sample_opponents(spec, np.random.default_rng(0), factory)
    assert len(opponents) == 1 and len(calls) == 1
    mask = np.zeros(enc.NUM_ACTIONS, dtype=bool)
    mask[[4, 9]] = True
    assert opponents[0].decide(np.zeros(enc.OBS_SIZE, np.float32), mask) in {4, 9}


# Training loop


@smoke
def test_epsilon_schedule_falls_then_holds():
    config = DQNTrainConfig(total_steps=100, epsilon_fraction=0.1)
    assert epsilon_at(config, 0.0) == 1.0
    assert epsilon_at(config, 0.05) == pytest.approx(0.51)
    assert epsilon_at(config, 0.1) == pytest.approx(0.02)
    assert epsilon_at(config, 0.9) == pytest.approx(0.02)


@smoke
def test_updates_follow_the_replay_ratio():
    assert updates_for(10_240, 4.0, 512) == 80
    assert updates_for(0, 4.0, 512) == 0


@pytest.mark.slow
def test_dqn_training_runs_logs_and_resumes(tmp_path):
    dqn_config = DQNConfig(hidden_size=16, batch_size=64, buffer_size=4_000)
    settings = dict(workers=2, steps_per_worker=128, device="cpu", checkpoint_every=1,
                    learning_starts=256, snapshot_every_steps=512)
    log = tmp_path / "log.csv"
    train_dqn(DQNTrainConfig(total_steps=768, **settings), dqn_config, tmp_path / "run", log)
    first = pd.read_csv(log)
    assert first["round"].tolist() == [1, 2, 3]
    assert first["gradient_steps"].iloc[-1] > 0
    train_dqn(DQNTrainConfig(total_steps=1_280, **settings), dqn_config, tmp_path / "run", log)
    log_rows = pd.read_csv(log)
    assert log_rows["round"].tolist() == [1, 2, 3, 4, 5]
    assert log_rows["gradient_steps"].is_monotonic_increasing
    assert log_rows["buffer_size"].iloc[-1] > first["buffer_size"].iloc[-1]


# CartPole check, the same bar the PPO code has to clear


def train_cartpole_dqn(rounds, seed=0, steps=500, learning_rate=5e-4):
    # Rewards are scaled by 0.01 for training, so Q-values lie between 0 and 1 as they do
    # in Saltmarket. Scores below count the unscaled reward.
    env = gym.wrappers.TransformReward(gym.make("CartPole-v1"), lambda reward: 0.01 * reward)
    config = DQNConfig(gamma=0.99, n_step=3, learning_rate=learning_rate, batch_size=128,
                       buffer_size=50_000, target_update_every=250, hidden_size=64)
    dqn = DQN(4, 2, config, seed=seed)
    buffer = ReplayBuffer(config.buffer_size, 4, 2)
    collector = TransitionCollector(env, seed, 2, config.gamma, config.n_step)
    rng = np.random.default_rng(seed)
    for round_number in range(rounds):
        epsilon = max(0.02, 1.0 - round_number / (0.4 * rounds))
        policy = NumpyPolicy(dqn.online.numpy_weights())
        buffer.add(collector.collect(policy, steps, epsilon).transitions)
        if len(buffer) >= 1_000:
            for _ in range(steps // 2):
                dqn.update(buffer.sample(config.batch_size, rng))
    env.close()
    env = gym.make("CartPole-v1")
    policy = NumpyPolicy(dqn.online.numpy_weights())
    mask = np.ones(2, dtype=bool)
    scores = []
    for episode in range(20):
        obs, _ = env.reset(seed=10_000 + episode)
        score, done = 0.0, False
        while not done:
            obs, reward, terminated, truncated, _ = env.step(policy.greedy(obs, mask))
            score += reward
            done = terminated or truncated
        scores.append(score)
    env.close()
    return float(np.mean(scores))


@pytest.mark.slow
def test_dqn_solves_cartpole():
    assert train_cartpole_dqn(160) >= 475
