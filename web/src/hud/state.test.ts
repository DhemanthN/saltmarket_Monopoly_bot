import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import type { GameFixture } from "../contract/types";
import { dayCaption, money, shortName, signedMoney } from "./format";
import { applyEvent, initialHudState, netWorth, reduceHud } from "./state";

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

describe("trade feed", () => {
  it("names who answered the offer", () => {
    const names = ["You", "Wave (PPO)"];
    const offer = { proposer: 0, responder: 1, giveSpaces: [], takeSpaces: [1], giveCash: 0, takeCash: 0, givePasses: 0, takePasses: 0 };
    let state = initialHudState(2);
    state = applyEvent(state, { t: "trade_offer", seq: 1, turn: 3, offer } as never, names);
    state = applyEvent(state, { t: "trade_result", seq: 2, turn: 3, accepted: false } as never, names);
    expect(state.feed[0].text).toBe("Wave declined your offer");
  });
});

describe("day caption", () => {
  it("counts days and names the part of day", () => {
    expect(dayCaption(0, 24)).toBe("Day 1, dawn · turn 0");
    expect(dayCaption(30, 24)).toBe("Day 2, noon · turn 30");
    expect(dayCaption(18, 24)).toBe("Day 1, night · turn 18");
    expect(shortName("Wave (PPO)")).toBe("Wave");
  });
});
