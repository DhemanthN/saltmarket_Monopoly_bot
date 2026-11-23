// Module worker: loads Pyodide and the bundle, then plays a human seat that blocks on Atomics.wait.
import { loadPyodide } from "/node_modules/pyodide/pyodide.mjs";

let cell;
let engine;

self.onmessage = async ({ data }) => {
  if (data.type === "init") {
    cell = new Int32Array(data.sab);
    const marks = {};
    let last = performance.now();
    const mark = (name) => { const now = performance.now(); marks[name] = Math.round(now - last); last = now; };
    const py = await loadPyodide({ indexURL: "/node_modules/pyodide/", stdout: () => {}, stderr: () => {} });
    mark("loadPyodide");
    await py.loadPackage([
      "/vendor/numpy-2.4.6-cp314-cp314-pyemscripten_2026_0_wasm32.whl",
      "/vendor/tqdm-4.67.3-py3-none-any.whl",
    ]);
    mark("numpy+tqdm");
    const fetchBytes = async (name) => new Uint8Array(await (await fetch(`/bundle/${name}?v=3`)).arrayBuffer());
    py.unpackArchive(await fetchBytes("app.zip"), "zip", { extractDir: "/app" });
    py.FS.mkdirTree("/models");
    for (const name of ["two_player.npz", "dqn_two_player.npz", "observations.npz"]) {
      py.FS.writeFile(`/models/${name}`, await fetchBytes(name));
    }
    mark("unpack+models");
    py.runPython("import sys; sys.path.insert(0, '/app/src')\nfrom spike import loader");
    mark("import saltmarket");
    engine = py;
    const bytes = performance.getEntriesByType("resource").reduce((sum, e) => sum + e.transferSize, 0);
    self.postMessage({ type: "ready", bytes, marks, isolated: self.crossOriginIsolated, sab: typeof SharedArrayBuffer });
  } else if (data.type === "play") {
    let count = 0;
    const decide = (obs, mask) => {
      const legal = [];
      mask.toJs().forEach((on, i) => on && legal.push(i));
      obs.destroy(); mask.destroy();
      count += 1;
      Atomics.store(cell, 0, 0);
      self.postMessage({ type: "decision", count, legal });
      Atomics.wait(cell, 0, 0);
      return Atomics.load(cell, 1);
    };
    engine.globals.set("js_decide", decide);
    const summary = engine.runPython(`loader.play_human_game(${data.seed}, '${data.bot}', js_decide)`);
    self.postMessage({ type: "done", summary, decisions: count });
  }
};
