import { Vector3, PerspectiveCamera } from "three";
import { describe, expect, it } from "vitest";
import { CHART_DIR, CHART_TARGET, chartDistance } from "./chartFit";
import { LOT_RADIUS } from "./layout";

/** True when the ring's left and right edges project inside the frame at the chosen distance. */
function ringFitsWidth(width: number, height: number, inset: number): boolean {
  const d = chartDistance(width, height, inset, 42);
  const cam = new PerspectiveCamera(42, width / height, 0.3, 400);
  cam.position.copy(CHART_TARGET).addScaledVector(CHART_DIR, d);
  cam.lookAt(CHART_TARGET);
  cam.updateMatrixWorld();
  cam.updateProjectionMatrix();
  return [-1, 1].every((side) => Math.abs(new Vector3(side * LOT_RADIUS, 0, 0).project(cam).x) <= 1);
}

describe("chartDistance", () => {
  it("fits the ring across a 390 x 844 phone with the sheet open", () => {
    expect(ringFitsWidth(390, 844, 360)).toBe(true);
  });
  it("backs off further for a phone than a desktop", () => {
    expect(chartDistance(390, 844, 0, 42)).toBeGreaterThan(chartDistance(1440, 900, 0, 42));
  });
  it("backs off further when a sheet covers half a short frame", () => {
    expect(chartDistance(1440, 600, 300, 42)).toBeGreaterThan(chartDistance(1440, 600, 0, 42));
  });
});
