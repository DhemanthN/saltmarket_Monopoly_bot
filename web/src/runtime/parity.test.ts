/** Engine parity: the worker code path, run in Node, reproduces the recorded desktop games. */
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { loadPyodide, type PyodideAPI } from "pyodide";
import { beforeAll, describe, expect, it } from "vitest";
import type { GameEvent } from "../contract/types";
import { bootEngine, runGame, type GameSummary } from "./engineCore";
import { PYODIDE_VERSION } from "./protocol";

const root = resolve(__dirname, "../..");
const pyodideDir = resolve(root, "public/pyodide", `v${PYODIDE_VERSION}`);
const manifestPath = resolve(root, "public/runtime/manifest.json");
const ready = existsSync(pyodideDir) && existsSync(manifestPath);

/**
 * Probabilities in explanations are rounded to 4 places from float32 network output, and wasm
 * and native BLAS can differ in the last place. Non-integer numbers match within 5e-4; every
 * integer, string and the fingerprint must match exactly.
 */
function tolerant(value: unknown): unknown {
  if (typeof value === "number" && !Number.isInteger(value)) return expect.closeTo(value, 3);
  if (Array.isArray(value)) return value.map(tolerant);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, tolerant(v)]));
  }
  return value;
}

it("pins the Pyodide version installed from npm", () => {
  const pkg = JSON.parse(readFileSync(resolve(root, "node_modules/pyodide/package.json"), "utf8"));
  expect(PYODIDE_VERSION).toBe(pkg.version);
});

const suite = ready ? describe : describe.skip;

suite(
  ready
    ? "engine parity"
    : "engine parity (missing runtime: run `node web/scripts/fetch-pyodide.mjs` and `python scripts/build_web_runtime.py`)",
  () => {
    let py: PyodideAPI;

    beforeAll(async () => {
      py = await loadPyodide({
        indexURL: pyodideDir,
        packageCacheDir: pyodideDir,
        stdout: () => {},
        stderr: () => {},
      });
      await py.loadPackage("numpy");
      const manifest = JSON.parse(readFileSync(manifestPath, "utf8")) as { bundle: string };
      bootEngine(py, new Uint8Array(readFileSync(resolve(root, "public/runtime", manifest.bundle))));
    }, 60_000);

    for (const name of ["vs_ppo_2p", "vs_dqn_2p", "table_4p"]) {
      it(
        `replays ${name} exactly`,
        () => {
          const fixture = JSON.parse(readFileSync(resolve(root, "fixtures", `${name}.json`), "utf8"));
          const events: GameEvent[] = [];
          let asked = 0;
          const ask = () => fixture.answers[asked++] as number;
          const summary: GameSummary = runGame(py, fixture.config, [], ask, (json) => {
            events.push(...(JSON.parse(json) as GameEvent[]));
          });
          expect(asked).toBe(fixture.answers.length);
          expect(events).toEqual(tolerant(fixture.events));
          expect(summary.fingerprint).toBe(fixture.fingerprint);
          expect(summary.finalState).toEqual(fixture.finalState);
        },
        60_000,
      );
    }
  },
);
