# Reinforcement learning design

The agent is a neural network trained with PPO to play Saltmarket. This document explains
what it sees, what it can do, how it learns, and how it is measured.

## Environment

`SaltmarketEnv` in `src/saltmarket/rl/env.py` follows the Gymnasium API. The game loop
calls strategies directly and cannot pause by itself, so each game runs on a worker
thread. At each decision the game thread hands an observation to the env and waits for an
action. Only one side runs at a time, so games stay deterministic for a given seed.

Each step is one decision, not one turn. Decisions are requested only when there is a real
choice. Forced moves, such as rolling when the Brig offers no other option, cost nothing.

## Observation

The observation is a vector of 266 numbers, built by `encode` in `rl/encoding.py`. All
seats are relative to the agent, so slot 0 is always the agent, and one network plays both
2-player and 4-player tables.

| Block | Size | Contents |
| --- | --- | --- |
| Spaces | 28 × 6 | Owner by relative seat (4), building level, mortgaged |
| Players | 4 × 6 | Cash, position, in Brig, passes held, still in game, net worth |
| Groups | 8 × 3 | Share owned by agent, agent owns all, a rival owns all |
| Decision kind | 9 | One-hot flag for the kind of decision |
| Decision space | 28 | One-hot flag for the space being bought or auctioned |
| Amounts | 2 | Price of that space, amount of any debt |
| Trade offer | 6 | Cash each way, value of spaces each way, whether each side completes a group |
| Global | 5 | Share of spaces unowned, game progress, depot supply, port supply, table size |

## Actions and masking

Every decision uses one shared list of 108 actions, defined in `rl/encoding.py`.

| Actions | Count | Meaning |
| --- | --- | --- |
| Pass, Yes | 2 | Decline or stop, and accept or buy |
| Bid | 7 | 0.25 to 2.0 times list price |
| Build | 8 | Add a level to a group, on its lowest legal lot |
| Sell | 8 | Sell a level from a group |
| Mortgage | 28 | Mortgage a space |
| Unmortgage | 28 | Lift a mortgage |
| Brig | 3 | Roll, pay, or use a pass |
| Trade | 24 | Offer cash for a group's missing lots at 1.0, 1.5, or 2.0 times list price |

**Action masking** means the network scores all 108 actions, but illegal ones have their
score set so low that their probability is effectively zero. The agent never wastes time
learning the rules, and it can never make an illegal move. Masks are built from the same
rule checks the engine uses.

Three limits keep episodes manageable, and they also limit what the agent can do:

- Proposals are cash offers for one group's missing lots, at most once per turn. The agent
  cannot propose swaps, though it can accept any offer.
- Voluntary sales are offered only when the agent holds a whole group it could develop.
- A bid is a fixed multiple of list price, not an exact amount.

## Reward

The final reward is 1 for winning and 0 otherwise. A game that reaches the turn cap is won
by the richest player, and that also counts as a win in training.

A small shaping term rewards raising the agent's share of table net worth. It has the
potential-based form `shaping * (gamma * new_share - old_share)`, which gives earlier
feedback in a long game without changing which policy is best.

## PPO

`rl/ppo.py` implements PPO directly in PyTorch.

- **Actor-critic:** two networks with two hidden layers of 256 units. The actor picks
  actions, and the critic predicts how well the game will go.
- **GAE:** generalized advantage estimation measures how much better an action turned out
  than the critic expected.
- **Clipped objective:** limits how far one update can move the policy from the policy
  that collected the data, which keeps training stable.
- **Entropy bonus:** rewards keeping some randomness, so the agent keeps exploring.

A slow test checks that this code solves CartPole before it is trusted on Saltmarket.

## Training

`rl/train.py` runs parallel worker processes, each stepping its own env with a NumPy copy
of the policy. The main process runs each update on the GPU. Game simulation stays on the
CPU because it is branching Python. Run `main` uses 2-player and 4-player tables with equal
chance, and run `two_player` uses only 2-player tables (`--opponents 1`). Nothing else
differs between them.

| Stage | Starts at | Opponents |
| --- | --- | --- |
| `random` | 0% | `random`, `never_buy` |
| `simple` | 5% | Five basic bots |
| `full` | 20% | All 26 bots |
| `self_play` | 60% | All 26 bots, with 30% of seats filled by earlier versions of the agent |

Checkpoints are saved during training, so rerunning a run resumes it. A resumed run should
keep the same total step count, because stages are fractions of that total. Metrics are
logged to `results/training_log_<run>.csv`.

## Evaluation

`scripts/evaluate.py` uses seeds starting at 9,000,000,000. Training seeds are below 2^31,
so evaluation games can never repeat training games. By default the agent takes its most
likely legal action rather than sampling.

**A matchup is one complete game.**

- **2-player:** the agent plays each of the 26 bots an equal number of times, alternating
  who moves first.
- **4-player:** the agent sits with three distinct bots drawn at random from the pool, and
  each table is played in all four rotations, so the agent takes every seat.

Two seed sets exist. The default set was used to compare runs. `--fresh-seeds` uses a
separate set, and those are the numbers to quote, because they played no part in choosing
between runs.

Results are reported with 95% Wilson intervals, separately for each table size, overall
and per opponent, over all games and over decided games only. Per-opponent 4-player
figures count every game that bot was at the table, so those games overlap.

## DQN

`rl/dqn.py` implements a second learning algorithm, Double DQN with dueling heads, so PPO
can be compared against a different family of methods. It was trained on the same
2-player tables as the `two_player` PPO run. Results are in the "PPO vs. DQN" section of
`RESULTS.md`.

### How it differs from PPO

PPO learns a policy directly: a probability for each action. DQN learns a **Q-value** for
each action, the reward it expects after taking that action and playing well afterwards,
and then picks the action with the highest Q-value. PPO learns only from data the current
policy just collected and then throws it away. DQN keeps old data in a replay buffer and
learns from it many times, which is called learning **off-policy**.

| Piece | What it does |
| --- | --- |
| Dueling heads | A shared trunk (two hidden layers of 256 tanh units, like PPO) feeds a value head V(s) and an advantage head A(s, a). Q = V + A − mean of A over the legal actions. |
| Experience replay | A ring buffer holds the latest 500,000 transitions. Batches of 512 are drawn uniformly at random. |
| Target network | A copy of the network computes learning targets. It is refreshed every 2,000 gradient steps. |
| Double DQN | The online network picks the best legal next action and the target network scores it, which reduces overestimation. |
| Epsilon-greedy | With chance epsilon the agent plays a random legal action. Epsilon falls from 1.0 to 0.02 over the first 10% of training, then stays there. |
| n-step returns | Each transition sums 8 decisions of reward before bootstrapping, with discount 0.999. |
| Loss | Huber loss, Adam at learning rate 1e-4, gradient norm clipped at 10. |

**Masking.** Illegal actions get a Q-value of minus infinity. That happens when acting,
in the dueling mean (only legal actions count), and inside the target, so the argmax over
the next state can only choose a legal action. When a game ends there is no next state,
the stored discount is 0, and the target is just the reward. `torch.where` keeps the
minus infinity from turning into NaN.

**Evaluation reuses the PPO code.** Within one state, V(s) and the mean advantage are the
same for every action, so the action with the highest advantage also has the highest
Q-value. `DuelingQNetwork.numpy_weights` therefore exports the trunk plus advantage head as
the "actor" of a `PolicyWeights`, and `NumpyPolicy.greedy` plays the DQN agent unchanged.
`scripts/evaluate.py` runs on `models/dqn_two_player.npz` exactly as it does for PPO.

### Training setup

`rl/dqn_train.py` and `scripts/train_dqn.py` keep everything that is not part of the
algorithm the same as the `two_player` PPO run.

| Kept the same as PPO | Value |
| --- | --- |
| Tables | 2-player only |
| Curriculum and opponent pools | `CURRICULUM` from `rl/train.py`, imported, not copied |
| Budget | 20,000,000 decisions (DQN stops at the first round past it) |
| Workers | 20 processes, game simulation on the CPU, network updates on the RTX 5070 Ti |
| Reward | Win = 1, plus the same potential-based shaping (0.2) |
| Discount | 0.999 |
| Network size | Two hidden layers of 256 tanh units |
| Self-play | 30% of seats from the stage on, up to 5 snapshots, one saved about every 1M decisions |
| Seed | 0 |

Each round, every worker plays 512 decisions (10,240 in all) with an epsilon-greedy NumPy
copy of the network. While they play, the main process takes gradient steps on the GPU
using earlier data, so collection uses weights one round old. Off-policy learning
tolerates that. Each collected transition is used about 4 times (the replay ratio), which
gives 80 gradient steps per round. Learning starts once the buffer holds 50,000
transitions.

Self-play snapshots of the DQN agent play greedily with epsilon 0.05, because a Q-network
has no probabilities to sample from the way a PPO snapshot does.

**Resuming.** Checkpoints in `checkpoints/<run>/` hold the online and target networks, the
optimizer, the counters, the snapshots, and the whole replay buffer (`replay.npz`, about
1.2 GB when full). Rerunning `train_dqn.py` with the same `--run` picks up where it
stopped. The batch sampler is seeded from the round number, so it needs no saved state.

### Choices made without tuning

PPO's hyperparameters were not searched, so DQN's were not searched on Saltmarket either.
They are common published defaults, adjusted only for this problem's scale: a larger
batch and buffer because there are 20 workers, and n-step returns because the main reward
arrives only when a game ends, often hundreds of decisions later. The only check before
the real run was a 300,000-decision trial to measure speed. Its win rates were not used to
change anything.

### Verification

`test_dqn_solves_cartpole` (marked slow) trains this code on CartPole and requires an
average greedy score of at least 475 out of 500, the same bar as the PPO test. CartPole
uses smaller settings (64 hidden units, discount 0.99, 3-step returns, 80,000 steps). DQN
is less steady than PPO here. In trials before the test was written, 3 of 4 seeds scored
500 after 50,000 steps but seed 0 scored 101, and with 80,000 steps seed 0 scored 500. The
test uses seed 0 at 80,000 steps. Fast tests cover the
replay buffer, masked Double DQN targets, the dueling head, the NumPy export, n-step
returns, and the training loop's resume.
