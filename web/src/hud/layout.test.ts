import { describe, expect, it } from "vitest";
import { listChoices, liveBids, panelModel } from "./layout";
import { SAMPLE_DECISIONS } from "./samples";

describe("panelModel", () => {
  describe.each(SAMPLE_DECISIONS.map((d) => [d.kind, d] as const))("%s", (_kind, decision) => {
    const model = panelModel(decision);

    it("shows every legal action once and nothing else", () => {
      const shown = [...model.choices, ...(model.pass ? [model.pass] : [])].map((a) => a.id);
      expect(shown.sort()).toEqual(decision.legal.map((a) => a.id).sort());
    });

    it("has one primary, except auctions where the selected bid is primary", () => {
      if (decision.kind === "auction") expect(model.primary).toBeNull();
      else expect(model.primary).toBe(model.choices[0]);
    });
  });

  it("offers bid chips cheapest first, at the legal amounts only", () => {
    const auction = SAMPLE_DECISIONS.find((d) => d.kind === "auction")!;
    expect(panelModel(auction).bids.map((b) => b.amount)).toEqual([52, 105, 157, 210, 262]);
  });

  it("does not offer bids above the player's cash", () => {
    const auction = SAMPLE_DECISIONS.find((d) => d.kind === "auction")!;
    expect(panelModel(auction, 160).bids.map((b) => b.amount)).toEqual([52, 105, 157]);
  });

  it("makes rolling the primary Brig action", () => {
    const brig = SAMPLE_DECISIONS.find((d) => d.kind === "brig")!;
    expect(panelModel(brig).primary?.label).toBe("Roll for doubles");
  });

  it("falls back to the first action when Brig has no roll", () => {
    const brig = SAMPLE_DECISIONS.find((d) => d.kind === "brig")!;
    const noRoll = { ...brig, legal: brig.legal.filter((a) => a.label !== "Roll for doubles") };
    expect(panelModel(noRoll).primary?.label).toBe("Pay the fine");
  });
});

describe("liveBids", () => {
  const bid = (id: number, amount: number) => ({ id, label: "Bid", amount, group: null, space: null, offer: null });

  it("drops chips at or under the high bid", () => {
    expect(liveBids([bid(1, 22), bid(2, 135), bid(3, 180)], 135).map((b) => b.id)).toEqual([3]);
  });

  it("returns no chips when none beats the high bid, leaving only Pass", () => {
    expect(liveBids([bid(1, 22), bid(2, 135)], 360)).toEqual([]);
  });
});

describe("listChoices", () => {
  const act = (id: number) => ({ id, label: "Sell", amount: id, group: null, space: null, offer: null });
  const choices = [act(1), act(2), act(3)];

  it("lists the highlighted choice first for raise-cash decisions", () => {
    expect(listChoices("raise_cash", choices).map((a) => a.id)).toEqual([1, 2, 3]);
    expect(listChoices("liquidate", choices)).toHaveLength(3);
  });

  it("lists only the rest for decisions with a primary button", () => {
    expect(listChoices("build", choices).map((a) => a.id)).toEqual([2, 3]);
  });
});
