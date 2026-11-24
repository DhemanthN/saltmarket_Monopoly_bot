import { describe, expect, it } from "vitest";
import { spaces, RING_RADIUS } from "./board";
import { LANDMARKS, PROP_KINDS, flagGeometry, galleonGeometry, landmarkGeometry } from "./landmarkKit";
import { ROAD_WIDTH } from "./layout";

describe("landmark kit", () => {
  it("gives every space a signature prop, and every prop has a builder", () => {
    expect(LANDMARKS).toHaveLength(spaces.length);
    for (const kind of LANDMARKS) expect(PROP_KINDS).toContain(kind);
  });
  it("names the props the board promises", () => {
    expect(LANDMARKS[spaces.findIndex((s) => s.kind === "brig")]).toBe("brig");
    expect(LANDMARKS[spaces.findIndex((s) => s.name === "Tidal Mill")]).toBe("waterwheel");
    expect(LANDMARKS[spaces.findIndex((s) => s.name === "Saltworks")]).toBe("saltworks");
  });
  it("merges into one mesh that keeps clear of the ring road", () => {
    const { geometry, flags } = landmarkGeometry();
    const pos = geometry.getAttribute("position");
    let nearest = Infinity;
    for (let i = 0; i < pos.count; i += 1) nearest = Math.min(nearest, Math.hypot(pos.getX(i), pos.getZ(i)));
    expect(nearest).toBeGreaterThan(RING_RADIUS + ROAD_WIDTH / 2);
    expect(flags.length).toBeGreaterThan(0);
    expect(geometry.getAttribute("uv").count).toBe(pos.count);
  });
  it("lets flags and sails sway only where they hang free", () => {
    const flag = flagGeometry().getAttribute("aSway");
    const values = Array.from({ length: flag.count }, (_, i) => flag.getX(i));
    expect(Math.min(...values)).toBeCloseTo(0);
    expect(Math.max(...values)).toBeCloseTo(1);
    expect(galleonGeometry().getAttribute("aSway").count).toBe(galleonGeometry().getAttribute("position").count);
  });
});
