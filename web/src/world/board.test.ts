import { describe, expect, it } from "vitest";
import { districts } from "../styles/tokens";
import { DISTRICT_HEIGHT, RING_RADIUS, ringPosition, spaces } from "./board";

describe("board", () => {
  it("has 40 spaces in walking order, starting at Home Quay", () => {
    expect(spaces).toHaveLength(40);
    expect(spaces.map((s) => s.index)).toEqual([...spaces.keys()]);
    expect(spaces[0].name).toBe("Home Quay");
  });

  it("maps every district to a token colour and a silhouette height", () => {
    const found = new Set(spaces.map((s) => s.district).filter((d) => d !== null));
    expect([...found].sort()).toEqual(Object.keys(districts).sort());
    for (const name of Object.keys(districts)) {
      expect(DISTRICT_HEIGHT[name as keyof typeof districts]).toBeGreaterThan(0);
    }
  });

  it("places all spaces on the ring, distinct from each other", () => {
    const seen = new Set<string>();
    for (const s of spaces) {
      const { x, z } = ringPosition(s.index);
      expect(Math.hypot(x, z)).toBeCloseTo(RING_RADIUS, 6);
      seen.add(`${x.toFixed(3)},${z.toFixed(3)}`);
    }
    expect(seen.size).toBe(40);
  });
});
