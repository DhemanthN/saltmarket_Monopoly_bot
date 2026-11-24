/// <reference lib="webworker" />
/**
 * The engine worker: loads Pyodide, numpy and the Saltmarket bundle, then plays games.
 * A human decision is posted to the page and the worker blocks in `Atomics.wait` until the page
 * writes the answer into the shared cell, so the Python game runs once from start to finish.
 */
import type { PyodideAPI } from "pyodide";
import { bootEngine, runGame } from "./engineCore";
import {
  ABORTED,
  CELL_ABORT,
  CELL_ACTION,
  CELL_FLAG,
  LOAD_STEPS,
  PYODIDE_VERSION,
  type FromWorker,
  type LoadPhase,
  type ToWorker,
} from "./protocol";

declare const self: DedicatedWorkerGlobalScope;

const PYODIDE_URL = `/pyodide/v${PYODIDE_VERSION}/`;
const CACHE_NAME = "saltmarket-runtime";

let cell: Int32Array | null = null;
let engine: PyodideAPI | null = null;

function post(message: FromWorker): void {
  self.postMessage(message);
}

function phase(name: LoadPhase): void {
  const step = LOAD_STEPS.find((s) => s.phase === name)!;
  post({ type: "phase", phase: name, fraction: step.fraction });
}

async function fetchBytes(url: string): Promise<Response> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Could not fetch ${url} (${response.status})`);
  return response;
}

/** Opens the runtime cache, or returns null where Cache Storage is unavailable (some private windows). */
async function openCache(): Promise<Cache | null> {
  try {
    return await caches.open(CACHE_NAME);
  } catch {
    return null;
  }
}

/** Fetches a versioned file through Cache Storage, so the engine and weights load from disk next time. */
async function cachedBytes(url: string): Promise<Uint8Array> {
  const cache = await openCache();
  const hit = await cache?.match(url);
  if (hit) return new Uint8Array(await hit.arrayBuffer());
  const response = await fetchBytes(url);
  if (cache) {
    await cache.put(url, response.clone());
    for (const key of await cache.keys()) {
      if (!key.url.endsWith(url)) await cache.delete(key);
    }
  }
  return new Uint8Array(await response.arrayBuffer());
}

async function load(): Promise<void> {
  phase("core");
  const { loadPyodide } = (await import(/* @vite-ignore */ `${PYODIDE_URL}pyodide.mjs`)) as typeof import("pyodide");
  const py = await loadPyodide({ indexURL: PYODIDE_URL, stdout: () => {}, stderr: () => {} });
  phase("numpy");
  await py.loadPackage("numpy", { messageCallback: () => {} });
  phase("bundle");
  const manifest = (await (await fetch("/runtime/manifest.json", { cache: "no-cache" })).json()) as { bundle: string };
  const bundle = await cachedBytes(`/runtime/${manifest.bundle}`);
  phase("engine");
  bootEngine(py, bundle);
  engine = py;
  phase("ready");
}

function ask(decisionJson: string): number {
  const shared = cell!;
  if (Atomics.load(shared, CELL_ABORT)) throw new Error(ABORTED);
  post({ type: "decision", decision: JSON.parse(decisionJson) });
  Atomics.wait(shared, CELL_FLAG, 0);
  if (Atomics.load(shared, CELL_ABORT)) throw new Error(ABORTED);
  const action = Atomics.load(shared, CELL_ACTION);
  Atomics.store(shared, CELL_FLAG, 0);
  return action;
}

function play(message: Extract<ToWorker, { type: "play" }>): void {
  try {
    const emit = (eventsJson: string) => post({ type: "events", events: JSON.parse(eventsJson) });
    const summary = runGame(engine!, message.config, message.answers, ask, emit);
    post({ type: "done", summary });
  } catch (error) {
    const text = String(error);
    if (text.includes(ABORTED)) post({ type: "aborted" });
    else post({ type: "error", message: text });
  }
}

self.onmessage = async ({ data }: MessageEvent<ToWorker>) => {
  if (data.type === "init") {
    cell = new Int32Array(data.sab);
    try {
      await load();
    } catch (error) {
      post({ type: "error", message: String(error) });
    }
  } else if (data.type === "play") {
    play(data);
  }
};
