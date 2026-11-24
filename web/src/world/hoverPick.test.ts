import { describe, expect, it } from "vitest";
import { ringPosition, spaces } from "./board";
import { pickSpace, spaceLabel } from "./hoverPick";

describe("pickSpace", () => {
  it("finds each lot at its own centre", () => {
    for (let i = 0; i < spaces.length; i += 1) {
      const { x, z } = ringPosition(i);
      expect(pickSpace(x, z)).toBe(i);
    }
  });

  it("finds nothing over the plaza or open water", () => {
    expect(pickSpace(0, 0)).toBeNull();
    expect(pickSpace(30, 30)).toBeNull();
  });
});

describe("spaceLabel", () => {
  it("names the lot and its district or kind", () => {
    for (let i = 0; i < spaces.length; i += 1) expect(spaceLabel(i)).toContain(spaces[i].name);
    const lot = spaces.find((s) => s.district)!;
    expect(spaceLabel(lot.index)).toMatch(/district$/);
  });
});
