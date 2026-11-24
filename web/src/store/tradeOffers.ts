import type { Decision } from "../contract/types";

/** Turns before the same trade opportunity is offered to the person again. */
export const OFFER_COOLDOWN_TURNS = 12;

/** What the person was last asked about: which groups could be bought, and on which turn. */
export interface OfferMemory {
  signature: string;
  turn: number;
}

/** The groups a "propose" decision can buy into, as one comparable string. */
export function offerSignature(decision: Decision): string {
  return [...new Set(decision.legal.map((a) => a.group ?? "other"))].sort().join("|");
}

/**
 * Whether to show this "propose" decision. The engine asks every turn the person owns part of a
 * group, which is far too often. Ask when the set of groups is new, or after a cooldown; the same
 * decision stays visible however often the store looks at it. Returns the memory to keep.
 */
export function nextOfferMemory(memory: OfferMemory | null, decision: Decision): { ask: boolean; memory: OfferMemory | null } {
  const signature = offerSignature(decision);
  const fresh = memory === null || memory.signature !== signature || decision.turn - memory.turn >= OFFER_COOLDOWN_TURNS;
  if (fresh) return { ask: true, memory: { signature, turn: decision.turn } };
  return { ask: decision.turn === memory.turn, memory };
}
