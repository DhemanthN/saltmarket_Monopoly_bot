import gymnasium as gym
import numpy as np
import pytest
import torch

from conftest import give, make_state
from saltmarket.bots.catalog import make_bot
from saltmarket.engine.game import Game
from saltmarket.engine.invariants import check_invariants
from saltmarket.rl import encoding as enc
from saltmarket.rl.agent import AgentStrategy
from saltmarket.rl.encoding import Context, DecisionKind
from saltmarket.rl.env import SaltmarketEnv
from saltmarket.rl.policy import NumpyPolicy
from saltmarket.rl.ppo import PPO, ActorCritic, Batch, PPOConfig, compute_gae
from saltmarket.rl.rollout import RolloutCollector, merge_batches

smoke = pytest.mark.smoke


def table(*names):
    return lambda rng: [make_bot(name) for name in names]


def random_table(rng):
    size = int(rng.choice([1, 3]))
    pool = ["balanced", "random", "always_buy", "aggressive_trader", "expert"]
    return [make_bot(str(n)) for n in rng.choice(pool, size=size)]


def run_env(env, seed, limit=200_000):
    """Play one episode with random legal actions, returning the action sequence."""
    rng = np.random.default_rng(seed)
    obs, info = env.reset(seed=seed)
    actions = []
    total = 0.0
    for _ in range(limit):
        legal = np.flatnonzero(info["action_mask"])
        assert len(legal) >= 1
        action = int(rng.choice(legal))
        actions.append(action)
        obs, reward, terminated, truncated, info = env.step(action)
        total += reward
        assert obs.shape == (enc.OBS_SIZE,) and np.isfinite(obs).all()
        if terminated:
            return actions, total, info
    raise AssertionError("episode did not finish")


# Encoding


@smoke
def test_action_blocks_do_not_overlap():
    starts = [enc.PASS, enc.YES, enc.BID, enc.BUILD, enc.SELL, enc.MORTGAGE, enc.UNMORTGAGE,
              enc.BRIG_ROLL, enc.BRIG_PAY, enc.BRIG_PASS, enc.TRADE, enc.NUM_ACTIONS]
    assert starts == sorted(set(starts))
    assert enc.NUM_ACTIONS == enc.TRADE + 24


@smoke
def test_observation_size_and_kind_flag():
    state = make_state(4)
    obs = enc.encode(state, 0, DecisionKind.BRIG, Context())
    assert obs.shape == (enc.OBS_SIZE,) and obs.dtype == np.float32


@smoke
def test_observation_is_relative_to_the_agent():
    state = make_state(4)
    give(state, 2, 6)
    seen_by_two = enc.encode(state, 2, DecisionKind.BUY, Context())
    seen_by_three = enc.encode(state, 3, DecisionKind.BUY, Context())
    start = enc.OWNABLE_SLOT[6] * enc.PER_SPACE
    assert seen_by_two[start] == 1
    assert seen_by_three[start] == 0
    assert seen_by_three[start + 3] == 1


# Masks


class Recorder:
    def __init__(self, action):
        self.action = action
        self.masks = []

    def __call__(self, obs, mask):
        self.masks.append(mask.copy())
        return self.action


def agent(state, action, seat=0):
    recorder = Recorder(action)
    bot = AgentStrategy(recorder)
    bot.reset(seat, np.random.default_rng(0))
    return bot, recorder


@smoke
def test_auction_mask_hides_unaffordable_bids(state):
    bot, recorder = agent(state, enc.BID)
    state.players[0].cash = 220
    assert bot.auction_bid(state, 39) == 105
    allowed = [i - enc.BID for i in np.flatnonzero(recorder.masks[0]) if i >= enc.BID]
    assert allowed == [0, 1]


@smoke
def test_auction_with_no_legal_bid_asks_nothing(state):
    bot, recorder = agent(state, enc.PASS)
    state.players[0].cash = 5
    assert bot.auction_bid(state, 39) == 0
    assert recorder.masks == []


@smoke
def test_build_mask_only_offers_buildable_groups(state):
    bot, recorder = agent(state, enc.PASS)
    give(state, 0, 6, 8, 1)
    assert list(bot.choose_builds(state)) == []
    assert set(np.flatnonzero(recorder.masks[0])) == {
        enc.PASS, enc.BUILD + enc.GROUPS.index("reef")
    }


@smoke
def test_no_build_decision_without_a_group(state):
    bot, recorder = agent(state, enc.PASS)
    give(state, 0, 6)
    assert list(bot.choose_builds(state)) == []
    assert recorder.masks == []


@smoke
def test_brig_with_only_one_option_is_not_a_decision(state):
    bot, recorder = agent(state, enc.BRIG_ROLL)
    state.players[0].cash = 0
    bot.brig_choice(state)
    assert recorder.masks == []


@smoke
def test_trade_options_need_a_single_seller(state):
    bot, _ = agent(state, enc.PASS)
    give(state, 0, 1)
    give(state, 1, 2)
    assert bot._trade_options(state) == {}
    give(state, 1, 4)
    assert len(bot._trade_options(state)) == len(enc.TRADE_PREMIUMS)


@smoke
def test_proposal_is_asked_once_per_turn(state):
    bot, recorder = agent(state, enc.PASS)
    give(state, 0, 6)
    give(state, 1, 8)
    bot.propose_trade(state)
    bot.propose_trade(state)
    assert len(recorder.masks) == 1


@smoke
def test_raise_cash_never_offers_pass(state):
    bot, recorder = agent(state, enc.MORTGAGE + enc.OWNABLE_SLOT[6])
    give(state, 0, 6)
    next(iter(bot.raise_cash(state, 100)))
    assert not recorder.masks[0][enc.PASS]


# Environment


@smoke
def test_random_masked_actions_never_break_the_rules():
    env = SaltmarketEnv(random_table, seed=1)
    for seed in range(12):
        run_env(env, seed)
    env.close()


@smoke
def test_invariants_hold_with_random_agent_in_debug_games():
    def decide(rng):
        return lambda obs, mask: int(rng.choice(np.flatnonzero(mask)))

    for seed in range(6):
        rng = np.random.default_rng(seed)
        bots = [AgentStrategy(decide(rng)), make_bot("expert"), make_bot("aggressive_trader")]
        game = Game(bots, seed=seed, debug=True)
        game.play()
        check_invariants(game.state)


@smoke
def test_same_seed_gives_identical_episode():
    env = SaltmarketEnv(table("balanced", "random", "expert"), seed=3)
    first, first_return, _ = run_env(env, 9)
    second, second_return, _ = run_env(env, 9)
    env.close()
    assert first == second and first_return == second_return


@smoke
def test_masked_action_is_refused():
    env = SaltmarketEnv(table("balanced"), seed=2)
    _, info = env.reset(seed=2)
    illegal = int(np.flatnonzero(~info["action_mask"])[0])
    with pytest.raises(ValueError):
        env.step(illegal)
    env.close()


@smoke
def test_reset_mid_game_abandons_the_old_thread():
    env = SaltmarketEnv(table("balanced"), seed=2)
    env.reset(seed=2)
    old = env._thread
    env.reset(seed=3)
    assert not old.is_alive()
    env.close()
    assert env._thread is None


@smoke
def test_final_reward_is_win_or_nothing_without_shaping():
    env = SaltmarketEnv(table("never_buy"), seed=5)
    _, total, info = run_env(env, 5)
    env.close()
    assert total == float(info["won"])


@smoke
def test_shaping_telescopes_to_a_small_total():
    plain = SaltmarketEnv(table("balanced"), seed=6)
    shaped = SaltmarketEnv(table("balanced"), seed=6, shaping=0.5, gamma=1.0)
    _, plain_total, _ = run_env(plain, 6)
    _, shaped_total, _ = run_env(shaped, 6)
    plain.close()
    shaped.close()
    assert shaped_total == pytest.approx(plain_total - 0.5 * 0.5, abs=0.01)


# PPO


@smoke
def test_gae_on_a_hand_worked_example():
    rewards = np.array([1.0, 2.0], dtype=np.float32)
    values = np.array([0.5, 1.0], dtype=np.float32)
    dones = np.array([False, True])
    advantages, returns = compute_gae(rewards, values, dones, 9.0, gamma=0.9, lam=0.5)
    delta_1 = 2.0 - 1.0
    delta_0 = 1.0 + 0.9 * 1.0 - 0.5
    assert advantages[1] == pytest.approx(delta_1)
    assert advantages[0] == pytest.approx(delta_0 + 0.9 * 0.5 * delta_1)
    assert returns == pytest.approx(advantages + values)


@smoke
def test_gae_does_not_leak_across_episodes():
    rewards = np.zeros(3, dtype=np.float32)
    values = np.zeros(3, dtype=np.float32)
    dones = np.array([True, False, False])
    rewards[2] = 5.0
    advantages, _ = compute_gae(rewards, values, dones, 0.0, gamma=1.0, lam=1.0)
    assert advantages[0] == 0.0 and advantages[1] == 5.0


@smoke
def test_masked_actions_get_zero_probability():
    model = ActorCritic(4, 6, 8)
    obs = torch.zeros(1, 4)
    mask = torch.tensor([[True, False, True, False, False, False]])
    log_prob, _, _ = model.evaluate(obs, mask, torch.tensor([1]))
    assert log_prob.item() < -1e6


@smoke
def test_numpy_policy_matches_torch():
    model = ActorCritic(5, 4, 16)
    policy = NumpyPolicy(model.numpy_weights())
    obs = np.arange(5, dtype=np.float32) / 5
    mask = np.array([True, True, False, True])
    expected_value = model.critic(torch.as_tensor(obs)).item()
    assert policy.value(obs) == pytest.approx(expected_value, abs=1e-5)
    action, log_prob, _ = policy.sample(obs, mask, np.random.default_rng(0))
    torch_log_prob, _, _ = model.evaluate(
        torch.as_tensor(obs)[None], torch.as_tensor(mask)[None], torch.tensor([action])
    )
    assert log_prob == pytest.approx(torch_log_prob.item(), abs=1e-4)


@smoke
def test_sampling_only_returns_legal_actions():
    policy = NumpyPolicy(ActorCritic(3, 5, 8).numpy_weights())
    rng = np.random.default_rng(0)
    mask = np.array([False, True, False, True, False])
    obs = np.ones(3, dtype=np.float32)
    assert {policy.sample(obs, mask, rng)[0] for _ in range(200)} == {1, 3}


def test_update_moves_policy_toward_rewarded_action():
    ppo = PPO(2, 2, PPOConfig(hidden_size=16, learning_rate=0.01, minibatch_size=64), seed=0)
    obs = np.ones((64, 2), dtype=np.float32)
    actions = np.array([0, 1] * 32)
    advantages = np.where(actions == 1, 1.0, -1.0).astype(np.float32)
    batch = Batch(
        obs, np.ones((64, 2), dtype=bool), actions,
        np.full(64, np.log(0.5), dtype=np.float32), advantages, np.zeros(64, dtype=np.float32),
    )
    for _ in range(5):
        ppo.update(batch)
    probabilities = torch.softmax(ppo.model.actor(torch.ones(1, 2)), dim=-1)
    assert probabilities[0, 1] > 0.8


@smoke
def test_collector_carries_masks_and_stats():
    env = SaltmarketEnv(table("never_buy"), seed=7)
    collector = RolloutCollector(env, seed=7, num_actions=enc.NUM_ACTIONS)
    policy = NumpyPolicy(ActorCritic(enc.OBS_SIZE, enc.NUM_ACTIONS, 16).numpy_weights())
    rollout = collector.collect(policy, 300, 0.99, 0.95)
    env.close()
    batch = rollout.batch
    assert batch.obs.shape == (300, enc.OBS_SIZE)
    assert batch.masks[np.arange(300), batch.actions].all()
    assert merge_batches([batch, batch]).actions.shape == (600,)


def train_cartpole(iterations, seed=0):
    env = gym.make("CartPole-v1")
    config = PPOConfig(gamma=0.99, learning_rate=1e-3, hidden_size=64, minibatch_size=256,
                       entropy_coef=0.0, epochs=10)
    ppo = PPO(4, 2, config, seed=seed)
    collector = RolloutCollector(env, seed=seed, num_actions=2)
    for _ in range(iterations):
        policy = NumpyPolicy(ppo.model.numpy_weights())
        rollout = collector.collect(policy, 2048, config.gamma, config.gae_lambda)
        ppo.update(rollout.batch)
    policy = NumpyPolicy(ppo.model.numpy_weights())
    scores = []
    mask = np.ones(2, dtype=bool)
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
def test_ppo_solves_cartpole():
    assert train_cartpole(40) >= 475
