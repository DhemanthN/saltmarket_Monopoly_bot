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
