import { TURNS_PER_DAY } from "../world/sun";

const DAY_PARTS = ["Dawn", "Noon", "Dusk", "Night"] as const;

export interface Telemetry {
  turn: number;
  /** One round is every seat taking a turn, so it is the turn count divided by the seat count. */
  round: number;
  timeOfDay: (typeof DAY_PARTS)[number];
  /** Cash of the person's seat, or null when nobody is playing (a watched game). */
  cash: number | null;
}

/** The numbers the chrome shows. All of them come from the game state, none are made up. */
export function telemetryFor(turn: number, seatCount: number, humanCash: number | null): Telemetry {
  const part = Math.floor(((((turn % TURNS_PER_DAY) + TURNS_PER_DAY) % TURNS_PER_DAY) / TURNS_PER_DAY) * 4);
  return {
    turn,
    round: Math.floor(turn / Math.max(1, seatCount)) + 1,
    timeOfDay: DAY_PARTS[part],
    cash: humanCash,
  };
}
