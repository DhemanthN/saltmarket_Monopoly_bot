import { seatOrder } from "../styles/tokens";
import { spaces } from "../world/board";

/** Formats a whole-number amount with thousands separators and a true minus (U+2212). */
export function money(amount: number): string {
  const text = Math.abs(amount).toLocaleString("en-US");
  return amount < 0 ? `−${text}` : text;
}

/** Formats a change with an explicit sign, so colour is never the only cue. */
export function signedMoney(delta: number): string {
  if (delta === 0) return "";
  return delta > 0 ? `+${money(delta)}` : money(delta);
}

export function spaceName(index: number): string {
  return spaces[index]?.name ?? `Space ${index}`;
}

/** Display names, in seat order: "You" for the human, the agent or bot name otherwise. */
export function seatNames(seats: readonly string[]): string[] {
  return seats.map((kind, i) => {
    if (kind === "human") return "You";
    const label = kind === "ppo" || kind === "dqn" ? kind.toUpperCase() : kind.replace(/_/g, " ");
    return `${seatOrder[i].label} (${label})`;
  });
}
