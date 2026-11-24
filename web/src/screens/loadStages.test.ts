import { describe, expect, it } from "vitest";
import { LOAD_STEPS } from "../runtime/protocol";
import { ROUTE_STOPS, stopAhead, stopReached } from "./loadStages";

describe("loading route", () => {
  it("has a stop for the harbour, every load step after the first, and the first scene", () => {
    expect(ROUTE_STOPS).toHaveLength(LOAD_STEPS.length + 1);
  });

  it("moves forward with each real phase and reaches the X only after the scene draws", () => {
    const reached = LOAD_STEPS.map((s) => stopReached(s.phase, false));
    expect(reached).toEqual([0, 1, 2, 3, 4]);
    expect(stopReached("ready", true)).toBe(ROUTE_STOPS.length - 1);
    expect(stopReached("core", true)).toBe(0);
  });

  it("names the stop ahead and none at the end", () => {
    expect(stopAhead(0)).toBe(1);
    expect(stopAhead(ROUTE_STOPS.length - 1)).toBeNull();
  });
});
