import { describe, expect, it } from "vitest";
import { Vector3 } from "three";
import { FLARE_MAX_S, FLARE_MIN_S, flareArc, flaresAllowed, galleonCount, nextFlareDelay, patrolCurve, PATROL_RADII, seededRandom } from "./effects";
import { RING_RADIUS } from "./board";

const open = { tier: "high", reducedMotion: false, calm: false, decisionOpen: false } as const;

describe("flare gate", () => {
  it("flies on High and Medium with motion allowed and no decision open", () => {
    expect(flaresAllowed(open)).toBe(true);
    expect(flaresAllowed({ ...open, tier: "medium" })).toBe(true);
  });
  it("never flies on Low, in Calm, with reduced motion or while a decision is open", () => {
    expect(flaresAllowed({ ...open, tier: "low" })).toBe(false);
    expect(flaresAllowed({ ...open, calm: true })).toBe(false);
    expect(flaresAllowed({ ...open, reducedMotion: true })).toBe(false);
    expect(flaresAllowed({ ...open, decisionOpen: true })).toBe(false);
  });
});

describe("flare timing and arc", () => {
  it("waits 15 to 20 seconds, repeatably for one seed", () => {
    const a = seededRandom(7);
    const b = seededRandom(7);
    for (let i = 0; i < 200; i += 1) {
      const d = nextFlareDelay(a);
      expect(d).toBeGreaterThanOrEqual(FLARE_MIN_S);
      expect(d).toBeLessThan(FLARE_MAX_S);
      expect(nextFlareDelay(b)).toBe(d);
    }
  });
  it("leaves the start, peaks at the middle and lands on the target", () => {
    const from = new Vector3(20, 1, 0);
    const to = new Vector3(14, 0, 2);
    expect(flareArc(from, to, 6, 0).distanceTo(from)).toBeCloseTo(0);
    expect(flareArc(from, to, 6, 1).distanceTo(to)).toBeCloseTo(0);
    expect(flareArc(from, to, 6, 0.5).y).toBeCloseTo(0.5 + 6);
    expect(flareArc(from, to, 6, -1).distanceTo(from)).toBeCloseTo(0);
  });
});

describe("patrol galleons", () => {
  it("sail only on High (3) and Medium (2)", () => {
    expect(galleonCount("high")).toBe(3);
    expect(galleonCount("medium")).toBe(2);
    expect(galleonCount("low")).toBe(0);
  });
  it("stay outside the reef on closed loops", () => {
    PATROL_RADII.forEach((_, i) => {
      const curve = patrolCurve(i);
      expect(curve.closed).toBe(true);
      for (let k = 0; k <= 50; k += 1) {
        const p = curve.getPointAt(k / 50);
        expect(Math.hypot(p.x, p.z)).toBeGreaterThan(RING_RADIUS + 6);
      }
    });
  });
});
