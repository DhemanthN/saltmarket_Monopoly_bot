import { describe, expect, it } from "vitest";
import type { Decision, LegalAction } from "../contract/types";
import { nextOfferMemory, OFFER_COOLDOWN_TURNS } from "./tradeOffers";

const action = (id: number, group: string): LegalAction => ({ id, label: `Offer ${id}`, amount: 10, group, space: null, offer: null });
const propose = (turn: number, groups: string[]): Decision => ({
  kind: "propose",
  seat: 0,
  turn,
  legal: groups.map((g, i) => action(i, g)),
  space: null,
  price: null,
  debt: null,
  offer: null,
});

describe("nextOfferMemory", () => {
  it("asks the first time and keeps asking about the same decision", () => {
    const first = nextOfferMemory(null, propose(5, ["kelp"]));
    expect(first.ask).toBe(true);
    expect(nextOfferMemory(first.memory, propose(5, ["kelp"])).ask).toBe(true);
  });

  it("stays quiet on later turns with the same groups", () => {
    const first = nextOfferMemory(null, propose(5, ["kelp"]));
    expect(nextOfferMemory(first.memory, propose(6, ["kelp"])).ask).toBe(false);
  });

  it("asks again for a new group or after the cooldown", () => {
    const first = nextOfferMemory(null, propose(5, ["kelp"]));
    expect(nextOfferMemory(first.memory, propose(6, ["kelp", "jade"])).ask).toBe(true);
    expect(nextOfferMemory(first.memory, propose(5 + OFFER_COOLDOWN_TURNS, ["kelp"])).ask).toBe(true);
  });
});
