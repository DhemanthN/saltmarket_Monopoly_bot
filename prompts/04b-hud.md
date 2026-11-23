Task 4b: hud. Read docs/web/handoff/contract.md and design-system.md, then
DESIGN.md (including the Mobbin picks). Start in plan mode. Runs at the same time as
task 4a; do not touch `web/src/world/`.

Build `web/src/hud/` against the contract types and fixture data:
- Decision panels for every decision kind in the contract: buy or pass, bid (the 7 bid
  multiples shown as amounts), build, sell, mortgage, unmortgage, Brig (roll, pay,
  use a pass), trade offer and response. One primary action each. Only legal actions
  are shown.
- Thought lanterns: for PPO, the top 3 actions with probability bars; for DQN, top 3
  Q-values. Hover or tap an opponent to open it. Label them plainly ("PPO's top
  choices"), never as invented reasoning.
- Ledger: cash and net worth per player with tabular figures; rent and trade feed.
- Start screen flow: pick opponent (PPO, DQN, or a bot), table size, start.
- Onboarding: three coach marks on the first game only.
- Game over: winner, turn count, and a link to RESULTS.md. Any win rate shown names its
  table size and comes from `results/`.
- Keyboard support for every decision; visible focus states.

Use Mobbin (via MCP) for anything DESIGN.md does not cover yet. Run `design-critic`
before calling it done. Handoff, commit, push.
