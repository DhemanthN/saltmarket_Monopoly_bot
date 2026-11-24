import { describe, expect, it } from "vitest";
import { stepTier, tierSettings, TierGovernor } from "./quality";

describe("TierGovernor", () => {
  it("steps down after three slow windows", () => {
    const g = new TierGovernor("high");
    expect(g.sample(20, 0)).toBeNull();
    expect(g.sample(20, 1000)).toBeNull();
    expect(g.sample(20, 2000)).toBe("medium");
  });

  it("steps back up after five healthy windows, which Low can now earn", () => {
    const g = new TierGovernor("low");
    const results = [0, 1, 2, 3, 4].map((i) => g.sample(60, i * 1000));
    expect(results).toEqual([null, null, null, null, "medium"]);
  });

  it("does not retry the tier it just left for a minute", () => {
    const g = new TierGovernor("high");
    for (let i = 0; i < 3; i += 1) g.sample(10, i * 1000);
    const early = [0, 1, 2, 3, 4].map((i) => g.sample(60, 5000 + i * 1000));
    expect(early.every((t) => t === null)).toBe(true);
    const late = [0, 1, 2, 3, 4].map((i) => g.sample(60, 70_000 + i * 1000));
    expect(late[4]).toBe("high");
  });

  it("ignores a middling window", () => {
    const g = new TierGovernor("medium");
    g.sample(20, 0);
    g.sample(45, 1000);
    g.sample(20, 2000);
    expect(g.tier).toBe("medium");
  });
});

describe("tierSettings", () => {
  it("caps pixel ratio at 1.5 on phones", () => {
    expect(tierSettings("high", 3, true).dpr).toBe(1.5);
    expect(tierSettings("high", 3, false).dpr).toBe(2);
  });
  it("clamps tier steps", () => {
    expect(stepTier("high", 1)).toBe("high");
    expect(stepTier("low", -1)).toBe("low");
  });
});
