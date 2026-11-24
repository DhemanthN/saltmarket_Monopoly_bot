import { describe, expect, it } from "vitest";
import { activeShake, getHeading, headingFromDirection, setHeading, shakeDecay, triggerCameraShake } from "./cameraBus";
import { INTRO_SECONDS, PARALLAX_AMOUNT, SWAY_AMOUNT, easeInOutCubic, introProgress, pointerUnit, shakeOffset, swayOffset } from "./cameraMotion";

describe("camera motion maths", () => {
  it("intro eases from 0 to 1 and stays there", () => {
    expect(introProgress(0)).toBe(0);
    expect(introProgress(INTRO_SECONDS / 2)).toBeCloseTo(0.5, 5);
    expect(introProgress(INTRO_SECONDS)).toBe(1);
    expect(introProgress(INTRO_SECONDS * 4)).toBe(1);
    expect(easeInOutCubic(0.25)).toBeLessThan(0.25);
  });

  it("sway stays tiny", () => {
    for (let t = 0; t < 60; t += 0.7) {
      const o = swayOffset(t);
      expect(Math.abs(o.x)).toBeLessThanOrEqual(SWAY_AMOUNT);
      expect(Math.abs(o.y)).toBeLessThanOrEqual(SWAY_AMOUNT);
    }
  });

  it("pointer maps the window to -1..1 and clamps", () => {
    expect(pointerUnit(0, 0, 1000, 500)).toEqual({ x: -1, y: -1 });
    expect(pointerUnit(500, 250, 1000, 500)).toEqual({ x: 0, y: 0 });
    expect(pointerUnit(5000, -9, 1000, 500)).toEqual({ x: 1, y: -1 });
    expect(PARALLAX_AMOUNT).toBeLessThan(1);
  });

  it("shake scales with strength", () => {
    expect(shakeOffset(0, 1.234)).toEqual({ x: 0, y: 0 });
    expect(Math.abs(shakeOffset(1, 0.2).x)).toBeGreaterThan(Math.abs(shakeOffset(0.2, 0.2).x));
  });
});

describe("camera bus", () => {
  it("heading is north at -Z, east at +X, and wraps to 0..359", () => {
    expect(headingFromDirection(0, -1)).toBe(0);
    expect(headingFromDirection(1, 0)).toBe(90);
    expect(headingFromDirection(0, 1)).toBe(180);
    expect(headingFromDirection(-1, 0)).toBe(270);
    setHeading(42);
    expect(getHeading()).toBe(42);
  });

  it("a shake decays to nothing and ends", () => {
    triggerCameraShake(0.8, 1, 1000);
    const s = activeShake(1100);
    expect(s).not.toBeNull();
    expect(shakeDecay(s!, 1000)).toBe(1);
    expect(shakeDecay(s!, 1500)).toBeCloseTo(0.25, 5);
    expect(activeShake(2100)).toBeNull();
  });

  it("ignores empty shakes", () => {
    triggerCameraShake(0, 1, 5000);
    expect(activeShake(5001)).toBeNull();
  });
});
