import { describe, expect, it } from "vitest";
import { EMBER_LIFE, EMBER_RISE, EmberPool, MAX_EMBERS } from "./emberPool";

describe("EmberPool", () => {
  it("starts empty", () => {
    expect(new EmberPool().step(0.1)).toBe(0);
  });

  it("drifts up and fades over its life, then frees the slot", () => {
    const pool = new EmberPool();
    pool.spawn(1, 2, 3);
    expect(pool.fade(0)).toBe(1);
    expect(pool.step(EMBER_LIFE / 2)).toBe(1);
    expect(pool.fade(0)).toBeCloseTo(0.5);
    expect(pool.positions[1]).toBeCloseTo(2 + EMBER_RISE / 2);
    expect(pool.step(EMBER_LIFE)).toBe(0);
    expect(pool.fade(0)).toBe(0);
  });

  it("never holds more than the cap and reuses the oldest slot", () => {
    const pool = new EmberPool();
    for (let i = 0; i < MAX_EMBERS + 5; i += 1) pool.spawn(i, 0, 0);
    expect(pool.step(0.01)).toBe(MAX_EMBERS);
    expect(pool.positions[0]).toBe(MAX_EMBERS);
  });

  it("tints colours by fade so dead slots are black", () => {
    const pool = new EmberPool();
    pool.spawn(0, 0, 0);
    pool.step(EMBER_LIFE / 2);
    pool.tint([1, 0.5, 0]);
    expect(pool.colors[0]).toBeCloseTo(0.5);
    expect(pool.colors[1]).toBeCloseTo(0.25);
    expect(pool.colors[3]).toBe(0);
  });
});
