# Results

Saltmarket is an original Monopoly-style game, so these findings apply to Saltmarket and
should not be read as findings about Monopoly. Every number below comes from a file in
`results/`, named next to the claim.

## Key findings

1. **The specialist agent is the strongest 2-player entrant.** On fresh held-out seeds it
   won 85.6% of 10,400 games (95% CI 84.9–86.2), ahead of the best bot at 83.4% (CI
   82.6–84.1). It beat all 26 bots head-to-head, with a lowest result of 61.5% (CI
   56.6–66.1) against `auction_sniper`. It missed the 90% target.
   `rl_eval_summary_two_player_fresh.json`, `rl_vs_bots_two_player_two_player_fresh.csv`,
   `figures/agent_vs_opponents.png`
2. **No agent clearly leads at 4 players.** The mixed agent won 40.7% of 10,000 games (CI
   39.8–41.7), level with `always_buy` at 41.0% (CI 39.9–42.1). On decided games it falls
   to 11th, at 37.1%. `rl_vs_bots_four_player_main_fresh.csv`
3. **The best strategy depends on table size.** `auction_sniper` is 1st at 2 players
   (83.4%) and 17th at 4 (19.7%). `two_player_win_rates.csv`,
   `four_player_win_rates.csv`, `figures/win_rates.png`
4. **Specializing mattered far more than anything else tried.** The same training code on
   2-player tables only raised the 2-player win rate from 71.2% to 85.6%.
   `rl_eval_summary_main_fresh.json`, `rl_eval_summary_two_player_fresh.json`,
   `figures/training_curves.png`
5. **The agent found the auction trick on its own.** It accepts list price rarely, as low
   as about 1% on driftwood, cinder, jade, and crown, yet it bids 85–166% of list price
   on average at auction. Winners only pay just over the runner-up's bid, so high bids can
   still be cheap. `rl_tendencies.csv`, `figures/agent_tendencies.png`
6. **Buying everything is a strong simple strategy.** `always_buy` is 2nd at 2 players
   (72.0%) and 1st at 4 (41.0%). `expert`, the bot designed to be best, is 14th of the
   26 bots at 2 players (60.7%). `two_player_win_rates.csv`, `four_player_win_rates.csv`
7. **Against 14 unseen bots the agent's win rate falls to 75.8%** (CI 74.7–76.9), from
   85.6% against its training bots. The `auction_sniper` baseline falls further on the
   same games, to 71.2%, so the new pool is harder overall, and the agent still leads by
   4.7 points. Its hardest new opponent is `leveraged_buyer` at 58.5% (CI 53.6–63.2).
   `rl_eval_heldout_bots.json`

## Unseen opponents

The agent trained against the same 26 bots it was evaluated on, so I wrote 14 new bots
afterwards and kept them out of every training stage (`docs/strategies.md`, "Held-out
bots"). The `two_player` specialist was not retrained. It played each new bot 400 times
at 2 players, alternating seats, on seeds no other evaluation uses. `auction_sniper`, the
best training bot, played the identical schedule as a baseline.
`rl_eval_heldout_bots.json`, `rl_eval_heldout_bots.csv`

| Pool | Agent | Agent, decided games | `auction_sniper` |
| --- | --- | --- | --- |
| 26 training bots | 85.6% (CI 84.9–86.2) | 87.1% | 83.4% (CI 82.6–84.1) |
| 14 held-out bots | **75.8% (CI 74.7–76.9)** | 78.1% (CI 77.0–79.2) | 71.2% (CI 70.0–72.3) |

**The win rate fell by about 10 points against unseen bots.** That drop is the honest
headline. Two things suggest it is mostly a harder pool rather than the agent failing
to generalize:

- **The baseline fell by more.** `auction_sniper` dropped about 12 points, from 83.4% to
  71.2%. Its training-pool figure comes from the tournament, which used different seeds
  and excluded itself, so the two rows are close but not identical comparisons.
- **The held-out pool has no easy opponents.** Against the training pool the agent won
  at least 95% against 8 of the 26 bots, including 100% against `random` and `never_buy`
  (`rl_eval_two_player_two_player_fresh.csv`). Its easiest held-out matchup is 86.5%,
  against `finisher`.

**The agent still beats the baseline on the same games.** On the 5,600 shared seeds the
agent won 917 games that `auction_sniper` lost, and lost 656 that it won. Overall it is
4.7 points ahead, and the intervals do not overlap. It won more than half its games
against every held-out bot.

**Hardest new opponents for the agent:**

| Bot | Agent win rate | `auction_sniper` win rate |
| --- | --- | --- |
| `leveraged_buyer` | 58.5% (CI 53.6–63.2) | 57.3% (CI 52.4–62.0) |
| `phase_shifter` | 63.8% (CI 58.9–68.3) | 64.5% (CI 59.7–69.0) |
| `mortgage_flipper` | 65.3% (CI 60.5–69.8) | 41.5% (CI 36.8–46.4) |
| `score_aware` | 67.8% (CI 63.0–72.1) | 64.8% (CI 59.9–69.3) |

The four hardest bots all spend aggressively in the land grab, by mortgaging, by
dropping their cash cushion, or by recycling dead lots into cash. A likely reason, not
tested here, is that cash-rich rivals make auctions less cheap, and both the agent and
`auction_sniper` rely on cheap auctions (Key finding 5). `mortgage_flipper`
is the clearest case: it beats `auction_sniper` 58.5% of the time, but the agent holds it
to 34.8%. With 400 games per bot, each per-opponent interval is about ±4.5 points, so
neighboring bots in this ranking are not clearly different.

7. **PPO beat DQN under identical training conditions.** A Double DQN agent trained the
   same way won 81.8% (CI 81.0–82.5), 3.8 points behind PPO (bootstrap CI 2.8–4.7,
   p < 10⁻¹²), and took twice as long to train. See "PPO vs. DQN" below.
   `ppo_vs_dqn.json`, `figures/ppo_vs_dqn.png`

## Which strategies win, and why

**Auctions are cheap at 2 players.** With one rival, a space often goes for little because
that rival has already spent its cash. `auction_sniper` wins 14.7 auctions per game at
16.3% of list price. `balanced` pays a similar 15.5% but wins only 7.7. At 4 players
competing bidders raise the sniper's price to 34.0% and cut its wins to 4.4 per game.
`auction_prices.csv`

**Stalled games are common at 4 players.** 26.1% of 4-player games hit the 2,000-turn cap,
against 4.2% of 2-player games. At 4 players, 70.6% of capped games had no group earned,
against 0.2% of decided games. Spaces end up split between players, few bots trade, and
nobody builds. `tournament_summary.json`, `figures/game_length.png`

**The mixed agent gains from stalled games.** It reaches the cap in 41.5% of its 4-player
games and wins 45.9% of those, which lifts its overall rank from 11th to 2nd. Training
counts a capped win as a full win, which is a likely cause, but this was not tested. The
specialist does not show the pattern, with a 2-player cap rate of 4.4%.
`rl_vs_bots_four_player_main_fresh.csv`, `rl_eval_summary_two_player_fresh.json`

**Building is strongly linked to winning.** At 2 players, win rate rises from 18.2% for
players who peaked at two depots to 60.0% at three and 80.7% at a port. At 4 players the
same steps are 0.9%, 19.5%, and 72.0%. This is an association, since players who are
already ahead can afford to build. `peak_level_win_rates.csv`,
`figures/building_level.png`

## Best groups

| Table size | Largest win-rate gap for earning a group | Highest rent per coin spent |
| --- | --- | --- |
| 2 players | driftwood, +41.7 points | reef, 1.90 |
| 4 players | crown, +47.2, and driftwood, +47.1 | reef, 5.74 |

Reef returns the most by a wide margin, which suggests it is underpriced in this board
design. Four-player returns run higher partly because long stalled games keep collecting
rent. Earning any group is linked to much higher win rates, but strong bots earn more
groups, so this does not prove the group caused the win. `two_player_group_value.csv`,
`four_player_group_value.csv`, `two_player_group_economics.csv`,
`four_player_group_economics.csv`, `figures/group_roi.png`

## PPO vs. DQN

A second agent was trained with Double DQN (dueling heads, experience replay, a target
network, epsilon-greedy exploration) to test whether the choice of algorithm matters.
It trained under the same conditions as the PPO specialist: 2-player tables, the same
curriculum and opponents, 20 million decisions, the same reward, and seed 0. Both were
evaluated on the same 10,400 fresh-seed games. Setup details are in `docs/rl.md`.
Source: `ppo_vs_dqn.json` unless another file is named.

**PPO is better.** The gap is small but clear.

| | PPO | DQN |
| --- | --- | --- |
| Win rate, all games | 85.6% (CI 84.9–86.2) | 81.8% (CI 81.0–82.5) |
| Win rate, decided games | 87.1% (CI 86.4–87.8) | 83.5% (CI 82.8–84.3) |
| Games reaching the turn cap | 4.4% | 3.9% |
| Rank among the 26 bots | 1st | 2nd, behind `auction_sniper` (83.4%) |
| Bots it beats significantly more often than the other agent does (p < 0.05) | 11 of 26 | 0 of 26 |
| Training time | 1,206 s | 2,467 s |
| Decisions per second | 16,606 | 8,109 |

- **Difference, all games:** PPO is ahead by 3.8 points. The two-proportion z-test gives
  z = 7.37, p = 1.7 × 10⁻¹³. A bootstrap that resamples games within each opponent (10,000
  replicates) gives a 95% interval of 2.8 to 4.7 points.
- **Difference, decided games:** 3.6 points, z = 7.14, p = 9.5 × 10⁻¹³, bootstrap interval
  2.6 to 4.5.
- **Per opponent:** DQN's largest gaps are against `expert` (81.3% vs. 89.5%),
  `coral_specialist` (91.8% vs. 99.0%), and `random` (93.8% vs. 100%). All 25 losses to
  `random` were decided games, not capped ones. DQN's best result relative to PPO is
  against `auction_sniper`, 65.3% vs. 61.5%, which is not significant (p = 0.27).
  `ppo_vs_dqn_per_opponent.csv`, `rl_eval_two_player_dqn_two_player_fresh.csv`
- **At 4 players,** where neither agent trained, DQN wins 17.9% (CI 17.2–18.7) against
  PPO's 37.1%. DQN carries over to a new table size much worse.
  `rl_eval_summary_dqn_two_player_fresh.json`, `rl_eval_summary_two_player_fresh.json`

![PPO vs. DQN](results/figures/ppo_vs_dqn.png)

**Sample efficiency has no clean winner.** No intermediate PPO weights were saved, so
the only learning curves are training win rates. These are not a fair skill measure:
PPO's training games sample from its probabilities, while DQN plays its best action
98% of the time after the first 10% of training. Each agent's self-play opponents are
also its own earlier versions. With that caveat, pooled per 500,000 decisions
(`ppo_vs_dqn_learning_curves.csv`):

| Stage | PPO training win rate | DQN training win rate |
| --- | --- | --- |
| `random` (0–1M) | 75.9% | 31.1% |
| `simple` (1–4M) | 43.0% | 62.3% |
| `full` (4–12M) | 67.9% | 78.4% |
| `self_play` (12–20M) | 73.2% | 73.8% |

After the full bot pool arrives at 4M decisions, DQN first reached 70% at 4.5M and PPO at
10.5M. DQN's curve peaked at 81.4% around 10M and then fell, and it ended at 72.7% in the
last bin against PPO's 78.6%. DQN learned faster in the middle of training, which is what
data reuse should give, but PPO ended stronger when both play greedily.

**Wall-clock time.** DQN took 2.0 times as long. In the training log, the median round
took 1.10 seconds in rounds 1–1,000 and 1.33 seconds after, and a median 0.75 and 0.85
seconds of that went to 80 small gradient steps in a row on the GPU. DQN also sends the
next observation with every transition, so more data moves between processes. Other
sessions were using the CPU during part of DQN training, so the timing is approximate.
These figures leave out DQN's first run, which reached 4.88M decisions before it was
stopped (see below). `training_log_dqn_two_player.csv`

**Likely reasons DQN lost.** These are explanations, not tested causes.

- **Long games, sparse reward.** A game lasts hundreds of decisions and the win arrives
  at the end. DQN passes value back 8 decisions per bootstrap step. PPO's advantage estimate
  looks over long stretches of real outcomes at once.
- **Close Q-values may make greedy play brittle.** If the legal actions in a state have
  similar Q-values, small errors can flip the argmax. This may explain the losses to
  `random`, whose play creates unusual states, but neither idea was measured.
- **Shifting opponents.** The curriculum and self-play change the opponents, so replayed
  experience goes stale. PPO learns only from fresh data.
- **Exploration.** Epsilon-greedy explores with uniformly random legal moves, such as
  random bids or mortgages, rather than near-good alternatives.

**This compares two trained agents, not two algorithms in general.** Each was trained
once with seed 0, and neither had its settings searched, so the variation between runs
is unknown. DQN also needed one fix. Its first run stalled at an 11–25% training win rate,
because Q-values started near 0.7 and the target network refreshed too rarely to correct
them. Those two settings were fixed, and the second run is the one reported.
`training_log_dqn_two_player_attempt1.csv`, `docs/rl.md`

## Methodology

| Stage | Size | Source |
| --- | --- | --- |
| Rules fuzz test | 10,000 random-bot games, invariants checked every turn | `fuzz_summary.json` |
| Bot fuzz test | 26 bots × 1,000 mixed-table games | `bot_fuzz.csv` |
| Held-out bot fuzz test | 14 bots × 1,000 games at tables drawn from all 40 bots | `bot_fuzz_heldout.csv` |
| Held-out evaluation | 5,600 games each for the agent and `auction_sniper`, 400 per held-out bot | `rl_eval_heldout_bots.json` |
| Landing check | 1,863,535 rolls against an exact Markov chain, 0.16% total variation distance | `landing_summary.json` |
| 2-player tournament | 130,000 games, 400 per pair, seats alternated | `tournament_summary.json` |
| 4-player tournament | 50,000 games, 12,500 tables in all four rotations | `tournament_summary.json` |
| Agent training | Two PPO runs and one DQN run of 20 million decisions | `training_log_main.csv`, `training_log_two_player.csv`, `training_log_dqn_two_player.csv` |
| Agent evaluation | 10,400 two-player and 10,000 four-player games per agent, per seed set | `rl_eval_summary_*.json` |

Tournament win rates have 95% Wilson intervals no wider than ±1.1 points over all games
(`tournament_summary.json`). Ratings use a Bradley-Terry fit on an Elo scale, from 2-player
games only (`ratings.csv`, `figures/ratings.png`). Rotating seats matters: the 4-player
first seat wins 26.3% and the last 23.4% (`four_player_seats.csv`).

**A matchup is one complete game.** The agent takes its most likely legal action, and its
evaluation seeds cannot occur in training. The quoted agent figures use a fresh seed set
that was not used to compare runs. See `docs/rl.md`.

## Limitations and threats to validity

- **Held-out opponents are a small, hand-written set.** The 14 unseen bots were written
  by the same author as the training bots, after training, and were not tuned against
  the agent. Truly different opponents, such as people, could do better against it.
  Only the 2-player specialist was tested against them.
- **One training run per setup.** Each agent comes from a single seed, so how much results
  vary between training runs is not measured. This includes the PPO vs. DQN comparison.
- **Little tuning.** Hyperparameters were not searched, and I did not test whether reward
  changes or longer training would help.
- **The bot pool shapes every ranking.** Win rates depend on which bots are in the pool,
  and the bots were hand-written for this project.
- **Agent and bot figures are close but not identical comparisons.** A bot's tournament
  games exclude itself and the agent, while the agent faces all 26 bots.
- **Capped games are decided by net worth.** Results are reported with and without them
  for this reason.
- **The agent has a limited action set.** It proposes only cash offers for a group's
  missing lots, cannot propose swaps, and bids in fixed steps.
- **Rule simplifications.** Auctions take one maximum bid per player, and there is no
  auction for the last depots during a shortage.
- **Group and building results are associations,** not causal effects.
