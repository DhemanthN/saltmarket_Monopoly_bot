import type { LoadPhase } from "../runtime/protocol";

/** Where the ship has to call on its way to the first scene. Each stop is a real engine load step. */
export const ROUTE_STOPS = [
  { id: "harbour", label: "Harbour" },
  { id: "runtime", label: "Runtime" },
  { id: "python", label: "Python" },
  { id: "code", label: "Game code" },
  { id: "models", label: "Models" },
  { id: "scene", label: "First scene" },
] as const;

/** The worker phase that is underway while the ship sails toward the stop after it. */
const PHASE_INDEX: Record<LoadPhase, number> = { core: 0, numpy: 1, bundle: 2, engine: 3, ready: 4 };

/**
 * Index of the last stop the ship has reached. A phase begins when the stop before it is done, so
 * `core` (runtime download) leaves the ship in the harbour and `ready` puts it one leg short of the
 * X, which it reaches once the first scene has drawn.
 */
export function stopReached(phase: LoadPhase, sceneDrawn: boolean): number {
  const base = PHASE_INDEX[phase];
  return phase === "ready" && sceneDrawn ? ROUTE_STOPS.length - 1 : base;
}

/** The stop the ship is heading for, or null once it is on the X. */
export function stopAhead(reached: number): number | null {
  return reached < ROUTE_STOPS.length - 1 ? reached + 1 : null;
}
