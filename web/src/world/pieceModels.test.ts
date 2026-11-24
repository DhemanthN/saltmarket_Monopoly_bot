import { describe, expect, it } from "vitest";
import { pieceModel } from "./pieceModels";
import { seatOrder } from "../styles/tokens";

const bbox = (g: ReturnType<typeof pieceModel>["body"]) => {
  g.computeBoundingBox();
  return g.boundingBox!;
};

describe("pieceModel", () => {
  const models = seatOrder.map((s) => pieceModel(s.emblem));

  it("gives every seat its own body shape", () => {
    const sizes = models.map((m) => {
      const b = bbox(m.body);
      return [b.max.x - b.min.x, b.max.y - b.min.y, m.body.getAttribute("position").count].map((n) => n.toFixed(2)).join("/");
    });
    expect(new Set(sizes).size).toBe(4);
  });

  it("keeps each piece on its plinth and under one board unit tall", () => {
    for (const m of models) {
      const b = bbox(m.body);
      expect(b.min.y).toBeGreaterThanOrEqual(-0.001);
      expect(b.max.y).toBeLessThan(1.1);
      expect(Math.max(b.max.x, -b.min.x, b.max.z, -b.min.z)).toBeLessThan(0.5);
    }
  });

  it("paints owner colour on cloth only, so the cloth mesh is never empty", () => {
    for (const m of models) expect(m.cloth.getAttribute("position").count).toBeGreaterThan(0);
  });
});
