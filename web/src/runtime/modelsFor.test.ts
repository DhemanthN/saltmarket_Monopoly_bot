import { describe, expect, it } from "vitest";
import { modelsFor } from "./engineCore";

describe("modelsFor", () => {
  it("loads only the weights the seats use", () => {
    expect(modelsFor(["human", "ppo"])).toEqual(["two_player"]);
    expect(modelsFor(["human", "dqn"])).toEqual(["dqn_two_player"]);
    expect(modelsFor(["human", "ppo", "expert", "ppo"])).toEqual(["main"]);
    expect(modelsFor(["human", "expert"])).toEqual([]);
  });
});
