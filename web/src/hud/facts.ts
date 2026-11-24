import type { AgentName } from "../contract/types";
import { RESULTS_FACTS, type ResultsFact } from "./resultsFacts";

export const RESULTS_URL = "https://github.com/DhemanthN/saltmarket-ai/blob/main/RESULTS.md";

/** The measured win rate for this agent at this table size, or null when `results/` has none. */
export function factFor(agent: AgentName, players: number): ResultsFact | null {
  return RESULTS_FACTS.find((f) => f.agent === agent && f.players === players) ?? null;
}

/** One sentence that always carries its table size and opponent pool. */
export function factSentence(fact: ResultsFact): string {
  const name = fact.agent === "ppo" ? "PPO" : "DQN";
  return `${name} won ${fact.winRate.toFixed(1)}% of ${fact.games.toLocaleString("en-US")} games at ${fact.players} players against the ${fact.bots} bots (95% CI ${fact.ciLow.toFixed(1)}–${fact.ciHigh.toFixed(1)}).`;
}
