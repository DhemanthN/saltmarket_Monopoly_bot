# Resume update

These are the measured results next to the original targets, with bullets you can use.
Nothing here goes beyond what the repo backs up.

## Targets against real results

| Target claim | Measured | Status |
| --- | --- | --- |
| 20+ strategy bots | 26 bots, 180,000 tournament games | Met |
| Finds which strategies win most often | Full rankings at 2 and 4 players, with 95% intervals | Met |
| Rules engine for Monopoly | Rules engine for an **original Monopoly-style game** | Changed |
| 40-space board, rent schedules, cards, jail | All built, as original designs | Met |
| RL agent on buying, building, and trading | PPO agent covers all three, plus bidding, mortgages, and jail choices | Met |
| Winning ~90% | **85.6%** at 2 players, 40.7% at 4 players | **Not met** |
| 10,000+ simulated matchups | 10,400 two-player games on fresh seeds | Met |

### The numbers behind the agent claim

| | 2-player specialist | Mixed agent |
| --- | --- | --- |
| Table size quoted | 2 players | 4 players |
| Games | 10,400 | 10,000 |
| Win rate | 85.6% | 40.7% |
| 95% interval | 84.9–86.2 | 39.8–41.7 |
| Decided games only | 87.1% | 37.1% |
| Opponents | Each of the 26 bots, 400 games each | Three distinct random bots per table |
| Rank among 27 | 1st | 2nd, or 11th on decided games |

A matchup means one complete game. Sources: `results/rl_eval_summary_two_player_fresh.json`
and `results/rl_eval_summary_main_fresh.json`.

## Recommended bullets

- Developed a Monte Carlo simulator running 180,000 games across 26 strategy bots to rank
  strategies in a Monopoly-style board game, with 95% confidence intervals within ±1.1 points
- Built a modular Python rules engine for an original Monopoly-style game, modeling a
  40-space board, rent schedules, card decks, jail, auctions, and trading, verified by 333
  tests and 10,000 fuzzed games
- Trained a PPO agent from scratch in PyTorch on buying, building, and trading decisions,
  winning 85.6% of 10,400 held-out 2-player games against 26 bots and beating every bot
  head-to-head

### Alternate versions

- Implemented PPO in PyTorch with action masking and curriculum training, producing a
  2-player agent that outperformed the best of 26 hand-built strategies (85.6% vs. 83.4%
  win rate over 10,000+ held-out games)
- Found through statistical analysis that a stalled-game effect inflated an RL agent's
  4-player ranking from 11th to 2nd, and that a measurement bug made every board group
  look equally decisive, then reported the first and fixed the second

## Wording to avoid

- "~90% win rate": the measured figure is 85.6%.
- "Winning 85.6% of matchups" without saying 2-player: the 4-player figure is 40.7%.
- "Monopoly rules engine" or "best Monopoly strategies": the game is original, and its
  findings do not transfer to Monopoly.
- "Beats unseen opponents": the agent trained against these same bots, and only the
  evaluation seeds were new.

## Skills line

| Skill | Verdict | Evidence |
| --- | --- | --- |
| Python | Keep | The whole project |
| Monte Carlo Simulation | Keep | 180,000-game tournaments and interval estimates |
| Reinforcement Learning | Keep | PPO, action masking, curriculum, self-play |
| Object-Oriented Design | Keep | `Strategy` hierarchy, `Game`, `SaltmarketEnv` |
| NumPy | Keep | Used throughout, including the Markov chain and policy inference |
| pytest | Keep | 333 tests with markers, fixtures, and parametrization |
| Git | Keep | Conventional commits throughout |
| PyTorch | **Add** | `rl/ppo.py` |
| PPO | **Add** | Written from scratch, verified on CartPole |
| pandas | **Add** | `analysis/tournament_stats.py` |
| matplotlib | **Add** | `analysis/plots.py` |
| GitHub Actions | **Add** | `.github/workflows/ci.yml` |
| Gymnasium | **Add** | `rl/env.py` |
| Hypothesis | Optional | One property-based test |
| seaborn | **Do not list** | It was planned, but no code used it, so it was removed |

Nothing on your current skills line needs removing.

## Likely interview questions

**1. Why did you build your own game instead of using Monopoly?**
An original game avoids copying a protected game's board, names, and cards. It keeps the
same kinds of mechanics, so the engineering and machine learning problems are the same. It
also meant I could not check against published Monopoly statistics, so I calculated exact
landing rates with a Markov chain. Those matched the simulation over 1.8 million rolls.

**2. What is PPO, and why use it here?**
PPO is a policy-gradient method. The agent plays games, estimates how much better each
action did than expected, and shifts toward the better ones. Its clipped objective limits
how far one update can move the policy, which keeps training stable. It handles a large
discrete action space well, and I checked my implementation on CartPole first.

**3. What is action masking, and why does it matter?**
The game has 108 possible actions, but only a few are legal at any moment. Masking gives
illegal actions zero probability, using the same rule checks as the engine. The agent never
has to learn the rules and cannot make an illegal move, so training goes toward strategy.

**4. Your target was 90%. Why did it reach 85.6%, and is that good?**
The best hand-written bot reaches 83.4%, so 90% was a high bar in a game with dice. My first
agent, trained on mixed tables, reached only about 71% at 2 players. Training on 2-player
tables alone raised that to 85.6%, and it beat every bot head-to-head. At 4 players the
result is weaker, and it trained against the same bots it was tested on. With more time I
would change how capped wins are rewarded and test it on unseen strategies.

**5. Tell me about a bug or a misleading result you found.**
Early results showed nearly every board group with about an 89% win rate, which looked
wrong. A bankrupt player's spaces go to the winner, so winners "completed" groups just as
they won. That was reverse causation. I wrote a failing test, counted only groups earned by
purchase, auction, or trade, and reran all 180,000 games. The win-rate tables came out
byte-identical, which proved only the measurement had changed.
