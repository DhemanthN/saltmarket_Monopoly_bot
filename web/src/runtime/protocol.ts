/** Messages between the page and the engine worker. */
import type { Decision, GameEvent, SessionConfig } from "../contract/types";
import type { GameSummary } from "./engineCore";

/** Pyodide version served from public/pyodide (see scripts/fetch-pyodide.mjs). */
export const PYODIDE_VERSION = "314.0.8";

/** Loading steps, in order. Each carries the share of the load finished when it starts. */
export const LOAD_STEPS = [
  { phase: "core", fraction: 0 },
  { phase: "numpy", fraction: 0.55 },
  { phase: "bundle", fraction: 0.65 },
  { phase: "engine", fraction: 0.72 },
  { phase: "ready", fraction: 1 },
] as const;

export type LoadPhase = (typeof LOAD_STEPS)[number]["phase"];

/**
 * Shared answer cells: [0] is the flag the worker waits on (the page sets it to 1 with an
 * answer, the worker sets it back to 0 once read), [1] the action id, and [2] a sticky abort
 * flag the worker checks before and after every wait. The page clears [2] when a game starts.
 */
export const CELL_FLAG = 0;
export const CELL_ACTION = 1;
export const CELL_ABORT = 2;
export const CELL_COUNT = 3;
/** Message text the worker uses when the page abandons a game. */
export const ABORTED = "The page left this game";

export type ToWorker =
  | { type: "init"; sab: SharedArrayBuffer }
  | { type: "play"; config: SessionConfig; answers: number[] };

export type FromWorker =
  | { type: "phase"; phase: LoadPhase; fraction: number }
  | { type: "events"; events: GameEvent[] }
  | { type: "decision"; decision: Decision }
  | { type: "done"; summary: GameSummary }
  | { type: "aborted" }
  | { type: "error"; message: string };
