// Shared Pyodide setup for the Node checks: mount the bundle and put the package on sys.path.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadPyodide } from "pyodide";

export const HERE = path.dirname(fileURLToPath(import.meta.url));
export const BUNDLE = path.join(HERE, "bundle");

export async function readyEngine() {
  const t0 = performance.now();
  const py = await loadPyodide({
    packageCacheDir: path.join(HERE, "vendor"),
    stdout: () => {},
    stderr: () => {},
  });
  await py.loadPackage(["numpy", "tqdm"]);
  const zip = new Uint8Array(fs.readFileSync(path.join(BUNDLE, "app.zip")));
  py.unpackArchive(zip, "zip", { extractDir: "/app" });
  py.FS.mkdirTree("/models");
  for (const name of ["two_player.npz", "dqn_two_player.npz", "observations.npz"]) {
    py.FS.writeFile(`/models/${name}`, fs.readFileSync(path.join(BUNDLE, name)));
  }
  py.runPython("import sys; sys.path.insert(0, '/app/src')");
  py.runPython("from spike import loader");
  return { py, readyMs: performance.now() - t0 };
}
