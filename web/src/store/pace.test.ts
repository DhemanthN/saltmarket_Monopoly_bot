import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import type { GameEvent } from "../contract/types";
import { holdsBeat } from "./pace";

const fixture = JSON.parse(readFileSync(resolve(__dirname, "../../fixtures/table_4p.json"), "utf8"));
const events: GameEvent[] = fixture.events;
const seats: string[] = fixture.config.seats;
const humanIndex = seats.indexOf("human");

const pick = (t: string, human: boolean) =>
  events.find((e) => e.t === t && "seat" in e && (e.seat === humanIndex) === human);

describe("holdsBeat", () => {
  for (const t of ["roll", "decision"]) {
    it(`holds a non-human ${t}`, () => {
      const event = pick(t, false);
      expect(event).toBeDefined();
      expect(holdsBeat(event!, seats)).toBe(true);
    });
    it(`shows the human ${t} at once`, () => {
      const event = pick(t, true);
      expect(event).toBeDefined();
      expect(holdsBeat(event!, seats)).toBe(false);
    });
  }

  it("never holds other event types", () => {
    const others = events.filter((e) => e.t !== "roll" && e.t !== "decision");
    expect(others.length).toBeGreaterThan(0);
    expect(others.some((e) => holdsBeat(e, seats))).toBe(false);
  });
});
