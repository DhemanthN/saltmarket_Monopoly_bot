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

## Methodology

| Stage | Size | Source |
| --- | --- | --- |
| Rules fuzz test | 10,000 random-bot games, invariants checked every turn | `fuzz_summary.json` |
| Bot fuzz test | 26 bots × 1,000 mixed-table games | `bot_fuzz.csv` |
| Landing check | 1,863,535 rolls against an exact Markov chain, 0.16% total variation distance | `landing_summary.json` |
| 2-player tournament | 130,000 games, 400 per pair, seats alternated | `tournament_summary.json` |
| 4-player tournament | 50,000 games, 12,500 tables in all four rotations | `tournament_summary.json` |
| Agent training | Two runs of 20 million decisions | `training_log_main.csv`, `training_log_two_player.csv` |
| Agent evaluation | 10,400 two-player and 10,000 four-player games per agent, per seed set | `rl_eval_summary_*.json` |

Tournament win rates have 95% Wilson intervals no wider than ±1.1 points over all games
(`tournament_summary.json`). Ratings use a Bradley-Terry fit on an Elo scale, from 2-player
games only (`ratings.csv`, `figures/ratings.png`). Rotating seats matters: the 4-player
first seat wins 26.3% and the last 23.4% (`four_player_seats.csv`).

**A matchup is one complete game.** The agent takes its most likely legal action, and its
evaluation seeds cannot occur in training. The quoted agent figures use a fresh seed set
that was not used to compare runs. See `docs/rl.md`.

## Limitations and threats to validity

- **Opponents are not held out.** Evaluation seeds are new, but the agent trained against
  these same 26 bots. Its win rate against unseen strategies is unknown.
- **One training run per setup.** Each agent comes from a single seed, so how much results
  vary between training runs is not measured.
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
