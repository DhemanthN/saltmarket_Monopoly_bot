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
