// Builds the engine bundle with scripts/build_web_runtime.py. Tries python3, python, then py.
// With no Python at all (some build images), falls back to the committed bundle in
// public/runtime/ and says so. Run `npm run runtime:assets` locally after engine changes and
// commit the result so the fallback stays current.
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const script = join(here, "..", "..", "scripts", "build_web_runtime.py");
const manifest = join(here, "..", "public", "runtime", "manifest.json");

for (const python of ["python3", "python", "py"]) {
  const probe = spawnSync(python, ["--version"], { stdio: "ignore" });
  if (probe.error || probe.status !== 0) continue;
  const run = spawnSync(python, [script], { stdio: "inherit" });
  process.exit(run.status ?? 1);
}

if (existsSync(manifest)) {
  console.warn("No Python found. Using the committed runtime bundle in public/runtime/.");
  process.exit(0);
}
console.error("No Python found and no committed runtime bundle. Install Python 3.9 or newer.");
process.exit(1);
