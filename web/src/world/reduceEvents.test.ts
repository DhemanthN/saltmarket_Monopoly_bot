import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import type { GameEvent, GameFixture } from "../contract/types";
import { applyEvent, initialState, reduceCount, reduceEvents } from "./reduceEvents";

const FIXTURES = resolve(__dirname, "../../fixtures");

interface IndexEntry {
  name: string;
  file: string;
}

function load(file: string): GameFixture {
  return JSON.parse(readFileSync(resolve(FIXTURES, file), "utf-8")) as GameFixture;
}

function deepFreeze<T>(value: T): T {
  if (value !== null && typeof value === "object" && !Object.isFrozen(value)) {
    Object.freeze(value);
    Object.values(value).forEach(deepFreeze);
  }
  return value;
}

const index: IndexEntry[] = JSON.parse(readFileSync(resolve(FIXTURES, "index.json"), "utf-8"));

describe.each(index)("event reducer: $name", ({ file }) => {
  const game = load(file);
  const seatCount = game.config.seats.length;
  const lastTurn = game.events[game.events.length - 1].turn;

  it("reduces all events to the engine's final state", () => {
    const state = reduceEvents(game.events, lastTurn, seatCount);
    const final = game.finalState;
    expect(state.applied).toBe(game.events.length);
    expect(state.cash).toEqual(final.cash);
    expect(state.owner).toEqual(final.owner);
    expect(state.level).toEqual(final.level);
    expect(state.mortgaged).toEqual(final.mortgaged);
    expect(state.position).toEqual(final.position);
    expect(state.bankrupt).toEqual(final.bankrupt);
  });

  it("reduceEvents at the last turn equals reduceCount over every event", () => {
    expect(reduceEvents(game.events, lastTurn, seatCount)).toEqual(
      reduceCount(game.events, seatCount, game.events.length),
    );
  });

  it("reduceEvents at a mid turn applies exactly the events up to that turn", () => {
    const mid = Math.floor(lastTurn / 2);
    const expected = game.events.filter((e) => e.turn <= mid).length;
    const state = reduceEvents(game.events, mid, seatCount);
    expect(state.applied).toBe(expected);
    expect(state).toEqual(reduceCount(game.events, seatCount, expected));
  });
});

describe("event reducer purity and board version", () => {
  const game = load(index[0].file);
  const seatCount = game.config.seats.length;

  it("never mutates the input state", () => {
    let state = deepFreeze(initialState(seatCount));
    for (const event of game.events) {
      const before = structuredClone(state);
      state = deepFreeze(applyEvent(state, event));
      expect(before.applied).toBe(state.applied - 1);
    }
    const frozen = deepFreeze(initialState(seatCount));
    const snapshot = structuredClone(frozen);
    game.events.forEach((e) => applyEvent(frozen, e));
    expect(frozen).toEqual(snapshot);
  });

  it("bumps boardVersion only on owner, build, sell, mortgage and unmortgage", () => {
    const boardEvents = new Set(["owner", "build", "sell", "mortgage", "unmortgage"]);
    const seen = new Set<string>();
    let state = initialState(seatCount);
    for (const event of game.events as GameEvent[]) {
      const next = applyEvent(state, event);
      const bump = next.boardVersion - state.boardVersion;
      expect(bump).toBe(boardEvents.has(event.t) ? 1 : 0);
      seen.add(event.t);
      state = next;
    }
    expect(seen.has("owner")).toBe(true);
  });
});
