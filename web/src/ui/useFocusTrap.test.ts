import { describe, expect, it } from "vitest";
import { wrapTarget } from "./useFocusTrap";

describe("wrapTarget", () => {
  it("wraps forward from the last control and pulls stray focus to the first", () => {
    expect(wrapTarget(3, 2, false)).toBe(0);
    expect(wrapTarget(3, -1, false)).toBe(0);
    expect(wrapTarget(3, 1, false)).toBeNull();
  });

  it("wraps backward from the first control and from outside", () => {
    expect(wrapTarget(3, 0, true)).toBe(2);
    expect(wrapTarget(3, -1, true)).toBe(2);
    expect(wrapTarget(3, 1, true)).toBeNull();
  });

  it("does nothing with no controls", () => {
    expect(wrapTarget(0, -1, false)).toBeNull();
  });
});
