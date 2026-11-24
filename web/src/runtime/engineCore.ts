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

/**
 * Weights files a game needs, by name in the manifest. Mirrors `agent_model` in
 * `src/saltmarket/web/seats.py`: PPO has a 2-player and a 4-player model, DQN only a 2-player one.
 */
export function modelsFor(seats: readonly string[]): string[] {
  const names = new Set<string>();
  for (const kind of seats) {
    if (kind === "dqn") names.add("dqn_two_player");
    else if (kind === "ppo") names.add(seats.length === 2 ? "two_player" : "main");
  }
  return [...names];
}

/** Puts weights at `/app/models/<name>.npz`, where the engine looks for them. */
export function installModel(py: PyodideAPI, name: string, bytes: Uint8Array): void {
  py.FS.mkdirTree("/app/models");
  py.FS.writeFile(`/app/models/${name}.npz`, bytes);
}

/** Unpacks the engine bundle (source and board data) to /app and imports it. */
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
