import type { SessionConfig } from "../contract/types";

/** The opponent the person picks for seat 1. Bots are a small named set, not every engine strategy. */
export type Opponent = "ppo" | "dqn" | "expert" | "balanced" | "always_buy";
export type TableSize = 2 | 3 | 4;
export const TABLE_SIZES: readonly TableSize[] = [2, 3, 4];

/** Plain labels for the opponent menu. Bot names match `scripts/record_fixtures.py`. */
export const OPPONENT_LABEL: Record<Opponent, string> = {
  ppo: "PPO agent",
  dqn: "DQN agent (2 players only)",
  expert: "Expert bot: builds and trades",
  balanced: "Balanced bot: buys most lots",
  always_buy: "Always-buy bot: never passes",
};

/** Bots fill the seats beyond the first opponent. */
const FILLER_BOTS = ["always_buy", "balanced"] as const;
const AGENT_DELAY_MS = 700;

/** DQN trained on two players only, so it is offered at a 2-player table only. */
export function opponentAllowed(opponent: Opponent, size: TableSize): boolean {
  return opponent !== "dqn" || size === 2;
}

/** Seats in order: the human, the chosen opponent, then bots to fill the table. */
export function buildConfig(opponent: Opponent, size: TableSize, seed: number): SessionConfig {
  if (!opponentAllowed(opponent, size)) throw new Error("DQN plays 2-player tables only");
  const seats = ["human", opponent, ...FILLER_BOTS.slice(0, size - 2)];
  return { seed, seats, agentDelayMs: AGENT_DELAY_MS };
}

/** How the person wants to play. Each mode maps to one seat table. */
export type Mode = "quick" | "ppo" | "dqn" | "table4" | "watch";
export const MODES: readonly Mode[] = ["quick", "ppo", "dqn", "table4", "watch"];

export const MODE_LABEL: Record<Mode, { title: string; note: string }> = {
  quick: { title: "Quick match", note: "You against the balanced bot. Starts at once." },
  ppo: { title: "Versus PPO", note: "You against the PPO agent." },
  dqn: { title: "Versus DQN", note: "You against the DQN agent. 2 players only." },
  table4: { title: "Table of 4", note: "You, the PPO agent and two bots." },
  watch: { title: "Watch bots", note: "Three bots play. You only watch." },
};

/** Bots that play each other in Watch mode: the same named set as the opponent menu. */
const WATCH_SEATS = ["expert", "balanced", "always_buy"] as const;

/** DQN needs a 2-player table. Every other mode works at any size. */
export function modeAllowed(mode: Mode, size: TableSize): boolean {
  return mode !== "dqn" || size === 2;
}

/** The table size a mode plays at; PPO and DQN follow the person's pick. */
export function modeSize(mode: Mode, picked: TableSize): TableSize {
  if (mode === "quick") return 2;
  if (mode === "table4") return 4;
  if (mode === "watch") return 3;
  return picked;
}

/** The seat table for a mode. `picked` is the table size chosen in the size control. */
export function buildModeConfig(mode: Mode, picked: TableSize, seed: number): SessionConfig {
  if (!modeAllowed(mode, picked)) throw new Error("DQN plays 2-player tables only");
  if (mode === "watch") return { seed, seats: [...WATCH_SEATS], agentDelayMs: AGENT_DELAY_MS };
  const opponent: Opponent = mode === "quick" ? "balanced" : mode === "dqn" ? "dqn" : "ppo";
  return buildConfig(opponent, modeSize(mode, picked), seed);
}
