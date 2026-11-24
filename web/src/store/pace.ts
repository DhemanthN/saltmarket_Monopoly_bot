/**
 * Which events the screen holds back so a person can follow the other seats. The engine
 * answers instantly; the store shows its events one beat at a time instead.
 */
import type { GameEvent } from "../contract/types";

const HUMAN = "human";

/**
 * True when `event` should wait one beat (the session's `agentDelayMs`) before it is shown:
 * the start of a turn by a bot or agent seat (its roll), and each decision an agent makes.
 * The person's own events are shown at once.
 */
export function holdsBeat(event: GameEvent, seats: readonly string[]): boolean {
  if (event.t !== "roll" && event.t !== "decision") return false;
  return seats[event.seat] !== HUMAN;
}
