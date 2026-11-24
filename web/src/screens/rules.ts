/**
 * Rule numbers quoted in "How to play". Each mirrors a field of `GameConfig` in
 * `src/saltmarket/engine/config.py`; `rules.test.ts` fails if they drift apart.
 */
export const RULES = {
  starting_cash: 1400,
  salary: 180,
  brig_fine: 60,
  max_brig_turns: 3,
  max_doubles: 3,
  depots_per_port: 4,
  group_rent_multiplier: 2,
  building_sale_fraction: 0.5,
} as const;

/** The rules summary, one short paragraph per topic. */
export const HOW_TO_PLAY: readonly { title: string; body: string }[] = [
  {
    title: "Moving",
    body: `Everyone starts with ${RULES.starting_cash.toLocaleString("en-US")} coins. On your turn, roll two dice and walk the ring road clockwise. Passing or landing on Home Quay pays ${RULES.salary}. Doubles earn another roll, but ${RULES.max_doubles} doubles in a row send you to The Brig.`,
  },
  {
    title: "Buying",
    body: "Land on an unowned lot, ferry or utility and you may buy it at its list price. Decline, and it goes to auction between all traders.",
  },
  {
    title: "Rent and building",
    body: `Landing on another trader's lot costs rent. Own a whole district and its bare rent is ${RULES.group_rent_multiplier}x. Then build depots evenly across the district; after ${RULES.depots_per_port} depots a lot can take a port.`,
  },
  {
    title: "The Brig",
    body: `Press Gang sends you to The Brig. Leave by paying ${RULES.brig_fine} or rolling doubles; after ${RULES.max_brig_turns} missed tries you pay and go.`,
  },
  {
    title: "Money trouble",
    body: `Short of cash, sell buildings back for ${RULES.building_sale_fraction * 100}% of their cost or mortgage lots. If you still cannot pay, you are bankrupt. The last trader standing wins.`,
  },
];
