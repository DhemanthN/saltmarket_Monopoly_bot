// Puts the Pyodide runtime under public/pyodide/v<version>/ so the site serves it itself
// (cross-origin isolation blocks most CDN files, and self-hosting keeps the load predictable).
// Core files are copied from node_modules/pyodide. The numpy wheel is not in the npm package, so
// it is downloaded once from the Pyodide CDN for the same version and checked against the
// sha256 in pyodide-lock.json. Safe to run repeatedly: files already in place are skipped.
import { createHash } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const WEB = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SOURCE = path.join(WEB, "node_modules", "pyodide");
const { version } = JSON.parse(fs.readFileSync(path.join(SOURCE, "package.json"), "utf8"));
export const PYODIDE_DIR = path.join(WEB, "public", "pyodide", `v${version}`);
const CORE = ["pyodide.mjs", "pyodide.asm.mjs", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"];
const PACKAGES = ["numpy"];

function sha256(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

async function main() {
  fs.mkdirSync(PYODIDE_DIR, { recursive: true });
  for (const name of CORE) {
    fs.copyFileSync(path.join(SOURCE, name), path.join(PYODIDE_DIR, name));
  }
  const lock = JSON.parse(fs.readFileSync(path.join(SOURCE, "pyodide-lock.json"), "utf8"));
  for (const name of PACKAGES) {
    const { file_name: file, sha256: expected } = lock.packages[name];
    const target = path.join(PYODIDE_DIR, file);
    if (fs.existsSync(target) && sha256(fs.readFileSync(target)) === expected) continue;
    const url = `https://cdn.jsdelivr.net/pyodide/v${version}/full/${file}`;
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Download failed (${response.status}): ${url}`);
    const bytes = Buffer.from(await response.arrayBuffer());
    if (sha256(bytes) !== expected) throw new Error(`Checksum mismatch for ${file}`);
    fs.writeFileSync(target, bytes);
    console.log(`downloaded ${file}`);
  }
  console.log(`pyodide v${version} ready in public/pyodide`);
}

await main();
