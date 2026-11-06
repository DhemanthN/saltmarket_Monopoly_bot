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
