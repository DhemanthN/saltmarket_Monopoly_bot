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
of the policy. The main process runs each update. Tables are 2-player or 4-player with
equal chance.

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

Results are reported with 95% Wilson intervals, separately for each table size, overall
and per opponent, over all games and over decided games only. Per-opponent 4-player
figures count every game that bot was at the table, so those games overlap.
