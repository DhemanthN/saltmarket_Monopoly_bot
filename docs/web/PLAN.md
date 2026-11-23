# Saltmarket 3D: build plan

Goal: a website where anyone can play Saltmarket against the real PPO and DQN agents,
inside a 3D atoll they walk around as their own piece. The browser runs the real Python
engine and the real trained weights. Nothing is re-implemented.

Date: 2026-11-23 · Repo: `DhemanthN/saltmarket-ai` · Visual rules: `DESIGN.md`, `ANTI_SLOP.md`

## 1. Concept

- **The atoll.** The 40 spaces form the ring road of a coral atoll. Home Quay (0), The Brig
  (14), Calm Waters (20) and Press Gang (31) are the landmark corners. The three ferries
  (5, 19, 30) are piers. The utilities are the Saltworks pans (12) and the Tidal Mill (27).
  The lagoon in the middle holds the market square, where auctions and trades happen, and
  the Brig rock.
- **Districts.** The 8 property groups are 8 districts on the ring: kelp, reef, coral,
  driftwood, amber, cinder, jade and crown. Each has its own silhouette and accent colour.
- **Two views.** Street view is third person behind the human's piece. Chart view is a
  tilt-shift overview drawn like a sea chart. The `C` key and one button toggle between them.
- **Thought lanterns.** A lantern floats above each agent piece. For PPO it lists the top 3
  legal actions with probabilities. For DQN it lists the top 3 legal actions with Q-values.
  Both come from the real forward pass, and both also show the critic's value estimate.
  Labels say plainly "PPO's top choices" and "DQN's top Q-values". Lanterns never show
  invented reasoning.
- **Replay scrubber.** After the game, a scrubber moves through the event log by turn. The
  world re-renders from `reduceEvents(events, turn)`. A "value river" line plots the critic's
  estimate per turn for each agent seat.
- **Opponents.** PPO plays `models/two_player.npz` at 2-player tables and `models/main.npz`
  at 4-player tables. DQN plays `models/dqn_two_player.npz`, and at 4-player tables it is
  labelled "trained on 2-player tables only". Any of the 40 bots can also fill a seat.
  Agents play greedily, as in `scripts/evaluate.py`, so the measured results apply.

## 2. What the code already gives us

Found by reading the repo for this plan.

- Strategy hooks live in `src/saltmarket/bots/base.py:12-66`: `should_buy`, `auction_bid`,
  `choose_liquidations`, `choose_unmortgages`, `choose_builds`, `brig_choice`,
  `propose_trade`, `accept_trade`, `raise_cash`. `engine/game.py` calls them synchronously.
  `Game.play` (`game.py:79-88`) is a plain loop with no pause hook. `rl/env.py` pauses it
  with a thread and a queue.
- `rl/agent.py` `AgentStrategy(decide)` already turns every hook into a call
  `decide(observation, mask) -> action` over 108 actions. A **human seat is an
  `AgentStrategy` whose `decide` blocks until the page sends a choice**, so the engine needs
  no change. The human gets the same action set as the agents: 7 bid multiples, cash-for-group
  trade proposals, and accept or decline on any offer.
- `NumpyPolicy` (`rl/policy.py`) has `greedy`, `sample` and `value`. `load_policy`
  (`rl/train.py:125-134`) reads the `.npz` keys `actor_{0,1,2}_{w,b}` and
  `critic_{0,1,2}_{w,b}`. All three model files hold both, with shapes 266→256→256→108
  (actor) and 266→256→256→1 (critic), and are about 1.1 MB each.
- **The critic is exported for both agents.** PPO's critic is V(s). For DQN, the exported
  "actor" is trunk plus advantage head and the "critic" is trunk plus value head
  (`rl/dqn.py:146-164`), so the true Q-value is `V + A - mean(A over legal actions)`. Both
  values include the 0.2 shaping term, so the UI calls them "value estimate", never win
  probability.
- The game fingerprint is `game_fingerprint` in `sim/fingerprint.py:30-53`. Golden hashes are
  in `tests/data/golden_games.json` and are tested in `tests/test_performance.py`.
- Pyodide fit: the engine, bots, `rl/policy.py`, `rl/encoding.py` and `rl/agent.py` need only
  numpy (no torch, no gymnasium). Board and card JSON are read lazily (`engine/board.py:83`,
  `engine/cards.py:73`), so `data/*.json` must ship with the package. Two risks for the
  spike: `rng.spawn` needs a recent numpy, and floating-point differences in the Markov maths
  of `bots/forecast.py` could change a bot's decision and break a fingerprint.

## 3. Runtime options

| | A: Pyodide in a Web Worker | B: FastAPI server | C: TypeScript port |
| --- | --- | --- | --- |
| Engine | The real Python package, unchanged | The real package, unchanged | A rewrite of the engine and 40 bots |
| Parity | Expected; proven by fingerprints | Exact (same CPython) | Hard; every rule is re-implemented |
| Human input | Worker blocks in `decide` on `Atomics.wait` over a `SharedArrayBuffer`; needs COOP/COEP headers | Thread per game plus a queue, as in `rl/env.py` | Native async |
| Hosting | Static files on Vercel, no server cost | Always-on server, cold starts, per-session state | Static |
| Offline | Works after first load | No | Yes |
| First load | About 10-15 MB (Pyodide, numpy, wheel, models), then cached | Small | Smallest |

**Recommendation: A.** It runs the exact engine and agents, so the CLAUDE.md rule "never
change the rules engine" holds, and it hosts as static files. Pyodide, numpy, the
`saltmarket` wheel, `data/*.json` and `models/*.npz` are self-hosted under
`web/public/runtime/`. Under `Cross-Origin-Embedder-Policy: require-corp` a CDN load would be
blocked anyway. Files are cached with immutable headers and Cache Storage.

Fallbacks, in order:
1. Inside A, if `Atomics.wait` is not available, use Pyodide JSPI (`run_sync`) so the worker
   can wait on the page without a `SharedArrayBuffer`.
2. If spike criterion 1 or 2 fails twice, switch to B and prove criteria 1-3 for it.

C is rejected: it duplicates thousands of lines of tested rules and gives up the fingerprint
guarantee.

### Spike pass criteria (task 1)

1. 10 seeded games under Pyodide (run in Node with the `pyodide` npm package) give the same
   `game_fingerprint` as desktop Python, using the schedule in `tests/data/golden_games.json`.
2. A human seat pauses the engine at a decision and resumes with a choice sent from the page.
   Shown in a browser with the COOP/COEP headers on the dev server.
3. PPO (`two_player.npz`) and DQN (`dqn_two_player.npz`) choose the same action in Pyodide as
   desktop `NumpyPolicy.greedy` on 100 recorded observations and masks.
4. Engine ready in under 8 s from a cold load and under 2 s from cache on the owner's laptop
   (median of 3 runs, numbers recorded).

## 4. The GameSession contract

TypeScript-ish pseudocode. The Python dataclasses are the source of truth.
`scripts/export_contract.py` generates `web/src/contract/types.ts` from them, and nobody
edits that file by hand.

```ts
type SeatKind = "human" | "ppo" | "dqn" | { bot: string };   // bot name from the bot registry
interface SessionConfig {
  seed: number;
  seats: SeatKind[];            // 2 to 4 seats
  agentDelayMs?: number;        // pause after each agent move, default 700
}

interface GameSession {
  start(cfg: SessionConfig): Promise<void>;         // loads the runtime once, plays to the first human decision
  current(): Decision | null;                       // pending human decision, else null
  submit(action: ActionId): Promise<SubmitResult>;  // rejects illegal ids; runs to the next human decision or game end
  events(sinceIndex?: number): GameEvent[];         // append-only log
  onEvent(cb: (e: GameEvent) => void): Unsubscribe;
  onDecision(cb: (d: Decision) => void): Unsubscribe;
  fingerprint(): string;                            // same hash as sim/fingerprint.py
  dispose(): void;
}

// Same members as rl/encoding.DecisionKind.
type DecisionKind = "buy" | "auction" | "build" | "liquidate" | "unmortgage"
                  | "brig" | "propose" | "accept" | "raise_cash";

interface Decision {
  kind: DecisionKind;
  seat: number;
  turn: number;
  space?: number; price?: number; debt?: number;   // from encoding.Context
  offer?: TradeOfferView;                          // set when kind is "accept"
  legal: LegalAction[];                            // legal actions only, derived from the agent mask
}
interface LegalAction { id: ActionId /* 0..107 */; label: string; amount?: number; group?: string; space?: number }
type SubmitResult = { ok: true } | { ok: false; reason: "illegal" | "not_your_turn" | "game_over" };

// Attached to every agent move.
interface Explanation {
  agent: "ppo" | "dqn";
  top: { id: ActionId; label: string; prob?: number /* PPO */; q?: number /* DQN */ }[];  // top 3 legal
  value?: number;                                  // critic estimate, shown as "value estimate"
}

type GameEvent = { turn: number; seq: number } & (
  | { t: "roll"; seat: number; dice: [number, number] }
  | { t: "move"; seat: number; path: number[]; passedHome: boolean }   // every space passed
  | { t: "buy"; seat: number; space: number; price: number }
  | { t: "auction_start"; space: number }
  | { t: "auction_bid"; seat: number; amount: number }
  | { t: "auction_win"; seat: number | null; space: number; amount: number }
  | { t: "rent"; from: number; to: number; space: number; amount: number }
  | { t: "build" | "sell"; seat: number; space: number; level: number }
  | { t: "mortgage" | "unmortgage"; seat: number; space: number; amount: number }
  | { t: "trade_offer"; from: number; to: number; offer: TradeOfferView }
  | { t: "trade_result"; accepted: boolean }
  | { t: "brig_in" | "brig_out"; seat: number; how?: "roll" | "pay" | "pass" }
  | { t: "card"; seat: number; deck: "tide" | "ledger"; text: string }
  | { t: "decision"; seat: number; kind: DecisionKind; action: ActionId; explanation?: Explanation }
  | { t: "bankrupt"; seat: number; creditor: number | null }
  | { t: "game_over"; winner: number; turns: number; byTurnCap: boolean }
);
```

Events come from the engine's existing event log (`record_log`) plus the seat wrappers. If the
log lacks a field, for example the path of a move, the web layer derives it. The engine is
never changed for the website. If it ever needs a hook, the hook comes with a test, and every
existing test and fingerprint stays identical.

## 5. Tasks

One pane per task. Each task starts in plan mode and ends with `docs/web/handoff/<task>.md`,
a commit and a push. Tasks 1 and 3 can run at the same time, and so can 4a and 4b.

| # | Task | Depends on | Acceptance criteria |
| --- | --- | --- | --- |
| 1 | spike-runtime | 0 | `spikes/runtime/` proof. Pass/fail table for the four criteria in section 3, each with command and numbers, in `handoff/spike-runtime.md`. Runtime chosen. The owner reviews before anything else starts. |
| 2 | contract | 1 | `src/saltmarket/web/session.py` with `GameSession`, `HumanSeat`, `AgentSeat`. Generated `web/src/contract/types.ts`. 5 recorded games in `web/fixtures/`: at least one against PPO, one against DQN, and one with an auction, a trade and a bankruptcy. Tests: human legality, round trip against a direct engine run, an explanation on every agent move, fixtures load. All existing tests and fingerprints unchanged. |
| 3 | design-system | 0 | `web/` scaffold: Vite, React, TypeScript, react-three-fiber, drei, Vitest, ESLint. COOP/COEP on the dev server if the spike chose A. Self-hosted fonts. `tokens.css` and `tokens.ts` from DESIGN.md. Panel, Button, Ledger row, Signboard, Toast. The start screen and a dev-only `/tokens` page. design-critic verdict SHIP. |
| 4a | world | 2, 3 | Atoll with 8 district silhouettes, palette texture, outlines, fog, instanced buildings, hopping pieces, coin carts, sun arc, both cameras, lantern anchors. Pure `reduceEvents` tested on the fixtures. Quality tiers and `window.__saltmarketPerf`. perf-auditor inside budget, design-critic SHIP. |
| 4b | hud | 2, 3 | A decision panel for every `DecisionKind` showing legal actions only, one primary action each, full keyboard support. Lanterns for PPO and DQN with plain labels. Ledger. Start flow. Three coach marks on the first game. Game over screen. Every number from `results/` with its table size. design-critic SHIP. |
| 5 | integrate | 4a, 4b | Worker runtime behind `GameSession`. Load progress shown as the atoll being built. Runtime and weights cached. One store. Agent move delay about 700 ms. Full games against PPO, DQN and bots at 2 and 4 players. Calm in-world error with retry. Worker-path parity test on 3 seeds. Python suite and Vitest green. The owner playtests locally. |
| 6 | deploy | 5 | `web/vercel.json` with COOP/COEP, long cache headers, rewrites if needed. `npm run build` and `npm run preview` pass. CI runs ruff, `pytest -m "not slow"` and Vitest. A `HOSTING NEEDED:` message is sent and the owner sets up Vercel. The live page shows zero console errors and `crossOriginIsolated === true`. |
| 7 | qa | 6 | qa-browser (10 smoke flows), perf-auditor and design-critic run against the preview URL. One ranked `docs/web/qa/fix-list.md` with severity, paths and finder. No fixes in this task. |
| 8 | polish | 7 | Fix list worked top-down. Replay scrubber and value river. README "Play it" section with the live URL and a GIF. Every number on the site and in the README checked against `results/`. qa-browser and design-critic run again. |

## 6. Testing

**Tested**
- Engine parity: fingerprints through the browser runtime (task 1), then through the worker
  path (task 5).
- Agent parity: greedy action and top-3 explanation match desktop `NumpyPolicy` on recorded
  observations.
- HumanSeat legality: only masked-legal actions are offered and illegal ids are rejected, with
  a property test over random games.
- GameSession contract: a round trip equals a direct engine run on the same seeds, events
  match the schema, and every agent move carries an explanation.
- The generated `types.ts` matches the Python dataclasses. CI fails on drift.
- `reduceEvents`: the final state on each fixture equals the engine's final state (cash,
  owners, levels, mortgages).
- Fixture files load and validate.
- The existing Python suite stays green, and `pytest -m smoke` stays under 30 seconds.

**Deliberately not tested**
- Pixel snapshots, CSS, animation timing, one render test per component, or the 3D scene
  graph. These change often and say little about correctness. The design-critic and
  perf-auditor reports and the live smoke flows cover how the site looks and performs.
