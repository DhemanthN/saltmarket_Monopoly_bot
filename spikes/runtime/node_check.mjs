// Criteria 1 (fingerprint parity) and 3 (agent action parity) under Pyodide in Node.
import fs from "node:fs";
import path from "node:path";
import { HERE, readyEngine } from "./common.mjs";

const golden = JSON.parse(fs.readFileSync(path.join(HERE, "../../tests/data/golden_games.json")));
const { py, readyMs } = await readyEngine();
console.log(`ready in ${(readyMs / 1000).toFixed(2)} s, numpy ${py.runPython("import numpy; numpy.__version__")}`);

let failed = false;
for (const table of [2, 4]) {
  const t0 = performance.now();
  const got = JSON.parse(py.runPython(`loader.fingerprints(${table}, 10)`));
  const want = golden[String(table)].slice(0, 10);
  const same = got.filter((g, i) => JSON.stringify(g) === JSON.stringify(want[i])).length;
  const bad = got.findIndex((g, i) => JSON.stringify(g) !== JSON.stringify(want[i]));
  console.log(`criterion 1, ${table} players: ${same}/10 fingerprints identical (${((performance.now() - t0) / 1000).toFixed(1)} s)`);
  if (bad >= 0) { failed = true; console.log("  first mismatch", JSON.stringify(got[bad]), JSON.stringify(want[bad])); }
}
for (const [name, file] of [["ppo", "two_player.npz"], ["dqn", "dqn_two_player.npz"]]) {
  const r = JSON.parse(py.runPython(`loader.policy_check('/models/${file}', '/models/observations.npz', '${name}')`));
  console.log(`criterion 3, ${name}: ${r.matches}/${r.total} actions identical, max logit diff ${r.max_logit_diff}`);
  if (r.matches !== r.total) failed = true;
}
process.exit(failed ? 1 : 0);
