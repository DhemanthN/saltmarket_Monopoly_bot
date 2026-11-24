import { describe, expect, it } from "vitest";
import { buildConfig, OPPONENT_LABEL, opponentAllowed } from "./startConfig";

describe("buildConfig", () => {
  it("seats the human first, then the opponent, then bots", () => {
    expect(buildConfig("ppo", 4, 7).seats).toEqual(["human", "ppo", "always_buy", "balanced"]);
    expect(buildConfig("expert", 3, 7).seats).toEqual(["human", "expert", "always_buy"]);
  });

  it("offers a small named set of bots", () => {
    expect(buildConfig("balanced", 2, 1).seats).toEqual(["human", "balanced"]);
    expect(Object.keys(OPPONENT_LABEL)).toHaveLength(5);
  });

  it("allows DQN at 2 players only", () => {
    expect(opponentAllowed("dqn", 2)).toBe(true);
    expect(opponentAllowed("dqn", 3)).toBe(false);
    expect(() => buildConfig("dqn", 4, 1)).toThrow();
    expect(buildConfig("dqn", 2, 1).seats).toEqual(["human", "dqn"]);
  });
});
