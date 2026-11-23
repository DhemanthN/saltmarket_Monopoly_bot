import { describe, expect, it } from "vitest";
import { panelModel } from "./layout";
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
