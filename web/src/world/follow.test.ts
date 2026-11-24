import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import type { GameFixture } from "../contract/types";
import { followSeatFor } from "./follow";
import { reduceCount } from "./reduceEvents";

describe("followSeatFor", () => {
  it("follows the winner at game end, not a bankrupt human (bots_3p)", () => {
    const game = JSON.parse(readFileSync(resolve(__dirname, "../../fixtures/bots_3p.json"), "utf-8")) as GameFixture;
    const end = reduceCount(game.events, game.config.seats.length, game.events.length);
    expect(end.winner).not.toBeNull();
    expect(followSeatFor(end, game.config.seats)).toBe(end.winner);
  });

  it("follows the human while the human is still playing", () => {
    expect(followSeatFor({ winner: null, bankrupt: [false, false] }, ["ppo", "human"])).toBe(1);
  });

  it("skips a bankrupt human for the first seat still playing", () => {
    expect(followSeatFor({ winner: null, bankrupt: [true, true, false] }, ["human", "ppo", "dqn"])).toBe(2);
  });
});
