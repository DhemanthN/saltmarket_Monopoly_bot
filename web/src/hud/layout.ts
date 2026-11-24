import type { Decision, DecisionKind, LegalAction } from "../contract/types";

/** Labels the engine gives to the "do nothing" action. Mirrors `PASS_LABELS` in `src/saltmarket/web/labels.py`. */
const PASS_LABELS: ReadonlySet<string> = new Set([
  "Decline and send it to auction",
  "Pass",
  "Done building",
  "Keep everything",
  "Done",
  "Make no offer",
  "Decline",
]);

export interface PanelModel {
  /** The one primary action. Null for auctions, where the selected chip's bid is primary. */
  primary: LegalAction | null;
  /** Non-pass actions in engine order, primary first. Digit keys 1-9 pick from here. */
  choices: LegalAction[];
  /** The visibly secondary "do nothing" action, when legal. */
  pass: LegalAction | null;
  /** Auction bid chips, cheapest first. */
  bids: LegalAction[];
}

const BRIG_ROLL = "Roll for doubles";

export function isPass(action: LegalAction): boolean {
  return PASS_LABELS.has(action.label);
}

/** Splits a decision's legal actions into primary, choices and pass. Only legal actions are ever returned. */
export function panelModel(decision: Decision, cash: number = Infinity): PanelModel {
  const pass = decision.legal.find(isPass) ?? null;
  const rest = decision.legal.filter((a) => !isPass(a));
  if (decision.kind === "auction") {
    const bids = rest.filter((a) => a.amount !== null && a.amount <= cash).sort((a, b) => (a.amount ?? 0) - (b.amount ?? 0));
    return { primary: null, choices: bids, pass, bids };
  }
  const roll = decision.kind === "brig" ? rest.find((a) => a.label === BRIG_ROLL) : undefined;
  const primary = roll ?? rest[0] ?? null;
  const choices = primary ? [primary, ...rest.filter((a) => a !== primary)] : [];
  return { primary, choices, pass, bids: [] };
}

/**
 * Decisions whose first action sells or mortgages something. Enter does not take it blindly
 * there; the player clicks the row or presses its number.
 */
export function enterSubmits(kind: DecisionKind): boolean {
  return kind !== "liquidate" && kind !== "raise_cash";
}

export const DECISION_TITLE: Record<DecisionKind, string> = {
  buy: "Buy or pass",
  auction: "Auction",
  build: "Build",
  liquidate: "Raise cash",
  unmortgage: "Lift a mortgage",
  brig: "In the Brig",
  propose: "Offer a trade",
  accept: "Trade offer",
  raise_cash: "Raise cash",
};

/** Auction chips that beat the highest bid so far. With none left, every chip stays so the panel never empties. */
export function liveBids(bids: LegalAction[], high: number): LegalAction[] {
  const live = bids.filter((b) => (b.amount ?? 0) > high);
  return live.length > 0 ? live : bids;
}
