import type { WorldState } from "./reduceEvents";

/**
 * Seat the street camera follows: the winner once there is one, else the human while still
 * playing, else the first seat still playing. The camera never ends on a bankrupt seat.
 */
export function followSeatFor(state: Pick<WorldState, "winner" | "bankrupt">, seatKinds: readonly string[]): number {
  if (state.winner !== null) return state.winner;
  const human = seatKinds.indexOf("human");
  if (human !== -1 && !state.bankrupt[human]) return human;
  return Math.max(0, state.bankrupt.findIndex((b) => !b));
}
