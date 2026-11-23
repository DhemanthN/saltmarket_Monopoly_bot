import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import type { GameFixture } from "./types";

const FIXTURES = resolve(__dirname, "../../fixtures");

interface IndexEntry {
  name: string;
  file: string;
}

function load(file: string): GameFixture {
  return JSON.parse(readFileSync(resolve(FIXTURES, file), "utf-8")) as GameFixture;
}

const index: IndexEntry[] = JSON.parse(readFileSync(resolve(FIXTURES, "index.json"), "utf-8"));

describe("recorded fixtures", () => {
  it("lists five games, with PPO and DQN opponents", () => {
    expect(index).toHaveLength(5);
    const seats = index.flatMap((entry) => load(entry.file).config.seats);
    expect(seats).toContain("ppo");
    expect(seats).toContain("dqn");
  });

  describe.each(index)("$name", ({ file }) => {
    const game = load(file);

    it("numbers its events in order and ends with game over", () => {
      game.events.forEach((event, i) => expect(event.seq).toBe(i));
      const last = game.events[game.events.length - 1];
      expect(last.t).toBe("game_over");
      if (last.t === "game_over") expect(last.winner).toBe(game.result.winner);
    });

    it("replays to the engine's final cash, owners, levels and mortgages", () => {
      const cash = new Map<number, number>();
      const owner = new Map<number, number | null>();
      const level = new Map<number, number>();
      const mortgaged = new Map<number, boolean>();
      for (const event of game.events) {
        if (event.t === "cash") cash.set(event.seat, event.balance);
        if (event.t === "owner") owner.set(event.space, event.seat);
        if (event.t === "build" || event.t === "sell") level.set(event.space, event.level);
        if (event.t === "mortgage" || event.t === "unmortgage") {
          mortgaged.set(event.space, event.t === "mortgage");
        }
      }
      const final = game.finalState;
      final.cash.forEach((value, seat) => expect(cash.get(seat) ?? value).toBe(value));
      final.owner.forEach((value, space) => expect(owner.get(space) ?? null).toBe(value));
      final.level.forEach((value, space) => expect(level.get(space) ?? 0).toBe(value));
      final.mortgaged.forEach((value, space) => expect(mortgaged.get(space) ?? false).toBe(value));
    });

    it("gives every agent decision an explanation", () => {
      for (const event of game.events) {
        if (event.t !== "decision") continue;
        const seat = game.config.seats[event.seat];
        if (seat === "ppo" || seat === "dqn") {
          expect(event.explanation?.agent).toBe(seat);
          expect(event.explanation?.top.length).toBeGreaterThan(0);
        } else if (seat === "human") {
          expect(event.explanation).toBeNull();
        }
      }
    });
  });
});
