// Criterion 2 in Node: the engine blocks in a human seat until the main thread answers
// through a SharedArrayBuffer. Choices come from a fixed rule, so desktop can replay them.
import { Worker, isMainThread, parentPort, workerData } from "node:worker_threads";
import { readyEngine } from "./common.mjs";

const SEED = 4242;
const BOT = "cash_hoarder";
const pick = (count, legal) => legal[(count * 7) % legal.length];

if (isMainThread) {
  const sab = new SharedArrayBuffer(8);
  const cell = new Int32Array(sab);
  const worker = new Worker(new URL(import.meta.url), { workerData: { sab } });
  let asked = 0;
  worker.on("message", (msg) => {
    if (msg.type === "decision") {
      asked += 1;
      Atomics.store(cell, 1, pick(msg.count, msg.legal));
      Atomics.store(cell, 0, 1);
      Atomics.notify(cell, 0);
    } else if (msg.type === "done") {
      console.log(`criterion 2 (node): game finished, ${asked} decisions each blocked then resumed`);
      console.log(`  result ${msg.summary}`);
      console.log(`  worker blocked ${msg.blockedMs.toFixed(0)} ms in Atomics.wait in total`);
      process.exit(0);
    }
  });
} else {
  const cell = new Int32Array(workerData.sab);
  const { py } = await readyEngine();
  let count = 0;
  let blockedMs = 0;
  const decide = (obs, mask) => {
    const legal = [];
    mask.toJs().forEach((on, i) => on && legal.push(i));
    obs.destroy(); mask.destroy();
    count += 1;
    Atomics.store(cell, 0, 0);
    parentPort.postMessage({ type: "decision", count, legal });
    const t0 = performance.now();
    Atomics.wait(cell, 0, 0);
    blockedMs += performance.now() - t0;
    return Atomics.load(cell, 1);
  };
  py.globals.set("js_decide", decide);
  const summary = py.runPython(`loader.play_human_game(${SEED}, '${BOT}', js_decide)`);
  parentPort.postMessage({ type: "done", summary, blockedMs });
}
