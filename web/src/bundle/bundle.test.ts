import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const root = resolve(__dirname, "../../..");
const runtime = resolve(root, "web/public/runtime");

/** List zip entries with Python's zipfile so the test needs no JS zip library. */
function zipNames(path: string): string[] {
  const code = "import sys,zipfile;print(chr(10).join(zipfile.ZipFile(sys.argv[1]).namelist()))";
  return execFileSync("python", ["-c", code, path], { encoding: "utf8" }).trim().split(/\r?\n/);
}

describe("runtime bundle", () => {
  execFileSync("python", [resolve(root, "scripts/build_web_runtime.py")], { cwd: root });
  const manifest = JSON.parse(readFileSync(resolve(runtime, "manifest.json"), "utf8"));
  const names = zipNames(resolve(runtime, manifest.bundle));

  it("holds what the worker imports and loads", () => {
    for (const needed of [
      "src/saltmarket/__init__.py",
      "src/saltmarket/engine/game.py",
      "src/saltmarket/rl/policy.py",
      "src/saltmarket/web/session.py",
      "src/saltmarket/web/live.py",
      "data/board.json",
      "data/cards.json",
      "models/main.npz",
      "models/two_player.npz",
      "models/dqn_two_player.npz",
    ]) {
      expect(names).toContain(needed);
    }
  });

  it("names the bundle by content hash", () => {
    expect(manifest.bundle).toMatch(/^app\.[0-9a-f]{12}\.zip$/);
    expect(existsSync(resolve(runtime, manifest.bundle))).toBe(true);
  });
});

describe("vercel.json", () => {
  const config = JSON.parse(readFileSync(resolve(__dirname, "../../vercel.json"), "utf8"));
  const rule = (source: string) =>
    Object.fromEntries(
      config.headers
        .filter((h: { source: string }) => h.source === source)
        .flatMap((h: { headers: { key: string; value: string }[] }) => h.headers)
        .map((h: { key: string; value: string }) => [h.key, h.value]),
    );

  it("isolates every page for SharedArrayBuffer", () => {
    const all = rule("/(.*)");
    expect(all["Cross-Origin-Opener-Policy"]).toBe("same-origin");
    expect(all["Cross-Origin-Embedder-Policy"]).toBe("require-corp");
  });

  it("caches the hashed bundle and Pyodide forever but not the manifest", () => {
    expect(rule("/runtime/app.(.*).zip")["Cache-Control"]).toContain("immutable");
    expect(rule("/pyodide/(.*)")["Cache-Control"]).toContain("immutable");
    expect(rule("/runtime/manifest.json")["Cache-Control"]).toContain("must-revalidate");
  });
});
