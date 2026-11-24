import { describe, expect, it } from "vitest";
import { buildConfig, opponentAllowed } from "./startConfig";

describe("buildConfig", () => {
  it("seats the human first, then the opponent, then bots", () => {
    expect(buildConfig("ppo", 4, 7).seats).toEqual(["human", "ppo", "always_buy", "balanced"]);
    expect(buildConfig("bot", 3, 7).seats).toEqual(["human", "expert", "always_buy"]);
  });

  it("allows DQN at 2 players only", () => {
    expect(opponentAllowed("dqn", 2)).toBe(true);
    expect(opponentAllowed("dqn", 3)).toBe(false);
    expect(() => buildConfig("dqn", 4, 1)).toThrow();
    expect(buildConfig("dqn", 2, 1).seats).toEqual(["human", "dqn"]);
  });
});
