/**
 * The part of the engine runtime that does not care where it runs. The Web Worker and the Node
 * parity test both call these two functions, so the test exercises the same path the site uses.
 */
import type { PyodideAPI } from "pyodide";
import type { FinalState, ResultView, SessionConfig } from "../contract/types";

/** What the engine returns once a game is over. */
export interface GameSummary {
  result: ResultView;
  fingerprint: string;
  finalState: FinalState;
}

/** Receives a `Decision` as JSON text, returns the chosen action id. May block. */
export type AskHuman = (decisionJson: string) => number;
/** Receives a JSON list of new events. */
export type EmitEvents = (eventsJson: string) => void;

/** Unpacks the engine bundle (source, board data, model weights) to /app and imports it. */
export function bootEngine(py: PyodideAPI, bundle: Uint8Array): void {
  py.unpackArchive(bundle, "zip", { extractDir: "/app" });
  py.runPython("import sys\nsys.path.insert(0, '/app/src')\nimport saltmarket.web.live");
}

/**
 * Plays one game to the end. `answers` are replayed into the first human decisions without
 * calling `ask`, which is how a restarted worker rebuilds the game in progress.
 */
export function runGame(
  py: PyodideAPI,
  config: SessionConfig,
  answers: readonly number[],
  ask: AskHuman,
  emit: EmitEvents,
): GameSummary {
  const playLive = py.pyimport("saltmarket.web.live").play_live;
  const seats = py.toPy([...config.seats]);
  const given = py.toPy([...answers]);
  try {
    const summary: string = playLive.callKwargs(config.seed, seats, ask, emit, { answers: given });
    return JSON.parse(summary) as GameSummary;
  } finally {
    seats.destroy();
    given.destroy();
    playLive.destroy();
  }
}
