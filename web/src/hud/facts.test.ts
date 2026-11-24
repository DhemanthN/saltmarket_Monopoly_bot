import { describe, expect, it } from "vitest";
import { factFor, factSentence } from "./facts";
import { lanternBars } from "./lanternBars";

describe("results facts", () => {
  it("names the table size and opponent pool in every sentence", () => {
    const fact = factFor("ppo", 2)!;
    expect(factSentence(fact)).toBe(
      "PPO won 82.0% of 40,000 games at 2 players against the 40 bots (95% CI 81.6–82.4).",
    );
  });

  it("has no fact for DQN at 4 players or any agent at 3 players", () => {
    expect(factFor("dqn", 4)).toBeNull();
    expect(factFor("ppo", 3)).toBeNull();
  });
});

describe("lanternBars", () => {
  it("shows PPO probabilities as percentages", () => {
    const bars = lanternBars({
      agent: "ppo",
      model: "m",
      value: 0,
      top: [
        { id: 1, label: "Buy", prob: 0.62, q: null },
        { id: 0, label: "Pass", prob: 0.38, q: null },
      ],
    });
    expect(bars.map((b) => b.figure)).toEqual(["62%", "38%"]);
  });

  it("shows DQN Q-values with a true minus and keeps at most three", () => {
    const bars = lanternBars({
      agent: "dqn",
      model: "m",
      value: 0,
      top: [1, 2, 3, 4].map((i) => ({ id: i, label: `a${i}`, prob: null, q: 1 - i })),
    });
    expect(bars).toHaveLength(3);
    expect(bars[2].figure).toBe("−2.00");
    expect(bars[0].share).toBe(1);
  });
});
