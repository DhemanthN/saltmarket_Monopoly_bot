import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import type { GameFixture } from "../contract/types";
import { money, signedMoney } from "./format";
import { netWorth, reduceHud } from "./state";

const FIXTURES = resolve(__dirname, "../../fixtures");
const index: { name: string; file: string }[] = JSON.parse(readFileSync(resolve(FIXTURES, "index.json"), "utf-8"));

describe("hud reducer", () => {
  describe.each(index)("$name", ({ file }) => {
    const game: GameFixture = JSON.parse(readFileSync(resolve(FIXTURES, file), "utf-8"));
    const names = game.config.seats.map((_, i) => `Seat ${i}`);
    const state = reduceHud(game.events, names);

    it("ends with the engine's cash and net worth", () => {
      game.finalState.cash.forEach((cash, seat) => {
        if (!game.finalState.bankrupt[seat]) expect(state.cash[seat]).toBe(cash);
      });
      game.result.netWorths.forEach((worth, seat) => expect(netWorth(state, seat)).toBe(worth));
    });

    it("reports the engine's winner and turn count", () => {
      expect(state.winner).toBe(game.result.winner);
      expect(state.turns).toBe(game.result.turns);
    });
  });
});

describe("format", () => {
  it("uses a true minus and explicit signs", () => {
    expect(money(-1200)).toBe("−1,200");
    expect(signedMoney(50)).toBe("+50");
    expect(signedMoney(-50)).toBe("−50");
    expect(signedMoney(0)).toBe("");
  });
});
