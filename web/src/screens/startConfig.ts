import type { SessionConfig } from "../contract/types";

export type Opponent = "ppo" | "dqn" | "bot";
export type TableSize = 2 | 3 | 4;

export const TABLE_SIZES: readonly TableSize[] = [2, 3, 4];

/** Bots that fill the seats beyond the first opponent. Names are from `scripts/record_fixtures.py`. */
const FILLER_BOTS = ["always_buy", "balanced"] as const;
const DEFAULT_BOT = "expert";

const AGENT_DELAY_MS = 700;

/** DQN was trained for two players only, so it is offered at a 2-player table only. */
export function opponentAllowed(opponent: Opponent, size: TableSize): boolean {
  return opponent !== "dqn" || size === 2;
}

/** Seats in order: the human, the chosen opponent, then bots to fill the table. */
export function buildConfig(opponent: Opponent, size: TableSize, seed: number): SessionConfig {
  if (!opponentAllowed(opponent, size)) throw new Error("DQN plays at 2-player tables only");
  const first = opponent === "bot" ? DEFAULT_BOT : opponent;
  const seats = ["human", first, ...FILLER_BOTS.slice(0, size - 2)];
  return { seed, seats, agentDelayMs: AGENT_DELAY_MS };
}
