# Strategies

Every bot subclasses `Strategy` in `src/saltmarket/bots/base.py`. Most build on
`HeuristicBot` in `bots/heuristic.py`, which buys with a cash cushion, builds evenly, and
evaluates trades by value. Each entry below explains what a bot tries to do. How well it
works is measured by the tournament, not assumed here.

## Baselines

### `random`
Picks uniformly among legal moves for every decision. It shows what no strategy at all
looks like, and it doubles as the fuzz-testing bot because it wanders into unusual states
that sensible play avoids.

### `never_buy`
Declines every purchase, bid, and trade. It can only earn salary and card money, so it
sets the floor: any bot that loses to it has a real problem.

### `always_buy`
Buys anything it can afford with no cash cushion, and builds the same way. It tests the
popular advice to buy everything, and shows the cost of having no money when rent is due.

### `balanced`
The plain `HeuristicBot`. It keeps a modest cushion, bids slightly above list price,
builds evenly, and leaves the Brig as soon as it can. Other bots change one idea at a time
from this reference point, so it works as the control group.

## Cash management

### `cash_hoarder`
Holds a large reserve and bids below list price. It should survive bad rent, but it may
buy too little to ever threaten anyone. It tests whether safety alone can win.

### `conservative_mortgager`
Treats mortgages as a last resort. It sells buildings before mortgaging when short of
cash, and repays any mortgage as soon as it can. It tests whether keeping every space
earning rent beats keeping buildings up.

## Space specialists

### `amber_specialist`
Pays up to 1.5 times list price for the amber group and offers to trade for it, buying
elsewhere only when flush with cash. Amber sits just past Calm Waters, and this bot tests
whether that location is worth overpaying for.

### `cinder_specialist`
Applies the same focus to cinder, the only four-lot group. Four lots are harder to
complete, but more spaces can earn rent once they are. It tests whether that trade-off
pays.

### `coral_specialist`
Applies the same focus to coral, the cheap group just before the Brig. Players leaving
the Brig skip past it, while cheap depots make it fast to develop.

### `high_roller`
Applies the same focus to the expensive jade and crown groups, which have the highest
rents and the highest costs. It tests whether expensive spaces justify their slow payback.

### `ferry_baron`
Applies the same focus to the three ferries, whose rent grows with the number owned and
needs no buildings. It tests whether income without building can compete.

### `no_utilities`
Behaves like `balanced` but refuses the two utilities. It tests whether skipping their
low, dice-dependent rent frees cash for better uses.

### `cheap_lots`
Buys only spaces priced at 200 or less, then builds early. It bets that many cheap
buildings arrive sooner than a few expensive ones.

### `premium_lots`
Buys only spaces priced at 200 or more. It keeps its money for the second half of the
board, at the risk of having nothing to collect on early.

### `roi_buyer`
Buys only spaces with above-median expected return. Scores come from the exact landing
probabilities in `engine/markov.py` multiplied by developed rent, divided by total cost.
It is the most directly data-driven buyer.

## Building

### `three_depots`
Takes every completed group to three depots before going higher, following the idea that
the third building is the biggest jump in rent.

### `aggressive_builder`
Keeps no building reserve and mortgages spaces outside its completed groups to fund more
buildings. It chases high rent as early as possible and is exposed if the rent does not
arrive in time.

### `port_rush`
Develops one group all the way to ports before starting another, concentrating its
strength instead of spreading it.

### `shortage_blocker`
Stops at four depots and never upgrades to a port. Upgrading returns depots to the bank,
so staying at four keeps supply tied up and can starve rivals of buildings.

### `rent_maximizer`
Builds wherever one more level adds the most rent per coin spent, rather than following
a fixed pattern.

## Brig

### `brig_stayer`
Leaves the Brig quickly while spaces are still for sale. Late in the game it stays as
long as it can, since sitting still avoids rivals' rent while its own spaces keep earning.

## Auctions and trading

### `auction_sniper`
Never pays list price. It declines every purchase so the space goes to auction, then bids
up to 75% of list price, hoping rivals are short of cash or uninterested.

### `group_blocker`
Pays up to double at auction when winning stops a rival from completing a group, and
demands a high price to trade. It plays to deny opponents rather than to advance itself.

### `aggressive_trader`
Offers 1.75 times list price for the lots it needs, proposes swaps when short of cash, and
accepts deals readily. It tests whether getting groups early is worth overpaying.

### `monopoly_trader`
Trades only to complete a group, and strongly resists any deal that completes a rival's.
It is the selective counterpart to `aggressive_trader`.

## Combined

### `expert`
Combines the ideas above. It spends freely while spaces are for sale, then sizes its
reserve to the largest rent a rival can currently charge. It pays extra at auction to
complete or block groups, trades with both cash and swaps, and stays in the Brig late in
the game. It was designed to be the strongest heuristic, but the tournament decides which
bot actually is, and that bot becomes the benchmark for the reinforcement-learning agent.

# Held-out bots

These 14 bots live in `src/saltmarket/bots/heldout/` and are registered in their own
catalog, `HELDOUT_BOTS`. No training stage uses them, and a test checks that every
curriculum pool excludes them. They exist to measure how the agent does against
strategies it has never seen. Each one is built around an idea none of the 26 training
bots uses. They were written after the agent was trained and were not tuned against it.

## Adaptive

These bots pick a new posture, meaning a full set of cash, bidding, and trading
settings, before every decision.

### `phase_shifter`
Plays three different games in sequence. While at least half the board is unsold it
buys everything with no cushion. After that it buys only spaces that advance a group or
block a rival, and trades hard, with cash and swaps, to finish a group. Once it owns a
group it stops proposing trades and mortgages its spare spaces to pay for buildings.

### `score_aware`
Compares its share of the table's net worth with an even split. More than 15% ahead, it
protects the lead with a large reserve and a high price for any trade. More than 15%
behind, it takes big risks: no cushion, generous trade offers, and mortgages to fund
buildings. In between it plays like `balanced`.

### `finisher`
Plays patiently with a large reserve until some rival's cash plus everything that rival
could sell or mortgage is less than two of its own biggest rents. Then it drops every
reserve, mortgages spare land to build, and sits in the Brig so the weak rival keeps
circling its spaces.

## Opponent modeling

### `rival_watcher`
Tracks how much of each group every rival holds. It pays more at auction the further a
rival is into a group, buys contested spaces even with almost no cash left, and refuses
any trade that would leave the other player with half or more of a group. `group_blocker`
reacts only at the last missing lot, while this bot contests groups from the first one.

### `leader_denier`
Models who is winning by net worth. It never trades with a rival who is ahead of it and
pays extra at auction to keep that leader out of groups the leader has started. At a
table of three or more it accepts slightly unfavorable deals from players who are
behind, using them as a counterweight to the leader.

### `cash_reader`
Reads every rival's cash before buying. If no rival could bid even 80% of the price, it
declines and wins the space at auction for little more than the richest rival's cash.
Otherwise it pays list price. Unlike `auction_sniper`, it skips list price only when
the auction is sure to be cheap.

### `reciprocator`
Remembers how each rival treats it. Accepted offers and fair incoming deals build trust,
and rejections and lowball offers lose it. It makes no offers to distrusted rivals and
demands a steep margin from them. It pays a little more to trusted partners. Every 50
turns, each grudge softens by one step.

## Trading

### `swap_negotiator`
Looks for swaps where both sides complete a group, for example its last reef lot for a
rival's last kelp lot. It prices the rival's side with the standard bot valuation and
adds just enough cash to make the deal acceptable. It proposes only when the group it
gets has at least 90% of the expected rent of the group it gives up, using Markov
landing rates. Otherwise it falls back to cash offers.

### `mortgage_flipper`
Exploits bots that value a space at list price whether or not it is mortgaged. When it
holds a lone lot in a group a rival has started, it mortgages that lot for half its
price, then offers it to the richest rival for 90% of the price. Together that is about
1.4 times the price in cash. It offers each lot to each rival once.

## Markov-aware

These bots use the exact Markov chain from `engine/markov.py`, starting from where
players stand now rather than from long-run averages. Helpers are in `bots/forecast.py`.

### `risk_manager`
Sizes its reserve to the rent it may owe over its next two rolls. For each roll it
works out the chance of ending on every space from its current position, then keeps the
expected rent plus 1.645 standard deviations. That is about a 95% upper estimate if the
rolls were independent. It pays to leave the Brig only if the fine still leaves that
reserve.

### `ambush_builder`
Builds just in time. It looks at where every rival can land in their next two rolls,
builds where expected rival landings times the extra rent per coin is highest, and
holds its cash when no rival is at least 15% likely to land on a buildable group soon,
unless it has more than 800 in cash.

### `npv_bidder`
Puts a coin value on each space: long-run landing chance, times the number of rivals,
times the rolls left in a typical game, times the rent it expects given who holds the
rest of the group, minus building costs. It buys when the value beats the price and
bids up to that value at auction. So it pays more at crowded tables and early on, and
almost nothing late in the game.

## Exploits and finance

### `stalemate_seeker`
Plays for the turn cap, where the richest player wins. It pays extra for a first lot in
any group a rival has started, never trades, builds only with a large cushion, rarely
lifts mortgages because the interest lowers its net worth, and sits in the Brig late in
the game.

### `leveraged_buyer`
Keeps a war chest of 450, enough to buy any space, during the land grab by mortgaging
ferries, utilities, and lots in groups a rival has started. Once less than 30% of the
board is unsold it lifts those mortgages and builds. `aggressive_builder` mortgages to
pay for buildings, while this bot mortgages to buy land.
