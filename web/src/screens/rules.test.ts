import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { RULES } from "./rules";

const CONFIG = new URL("../../../src/saltmarket/engine/config.py", import.meta.url);

describe("How to play rule numbers", () => {
  it("match the engine's GameConfig defaults", () => {
    const lines = readFileSync(CONFIG, "utf-8").split(/\r?\n/);
    for (const [field, value] of Object.entries(RULES)) {
      const line = lines.find((l) => l.trim().startsWith(`${field}:`));
      const match = line?.match(/=\s*([\d.]+)/) ?? null;
      expect(match, field).not.toBeNull();
      expect(Number(match![1]), field).toBe(value);
    }
  });
});
