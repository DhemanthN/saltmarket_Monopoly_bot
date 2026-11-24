import { describe, expect, it } from "vitest";
import { buildShipGeometry, triangleCount } from "./shipGeometry";

describe("buildShipGeometry", () => {
  const ship = buildShipGeometry();

  it("stays near the 3k triangle budget in three meshes", () => {
    const tris = triangleCount(ship);
    expect(tris).toBeGreaterThan(2000);
    expect(tris).toBeLessThan(4000);
    expect(Object.keys(ship)).toHaveLength(3);
  });

  it("carries vertex colours and no uv, so parts merge into one draw call each", () => {
    for (const g of Object.values(ship)) {
      expect(g.getAttribute("color")).toBeDefined();
      expect(g.getAttribute("uv")).toBeUndefined();
    }
  });
});
