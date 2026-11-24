/**
 * The one store for a game on screen. It owns the engine worker, receives the session's events,
 * and releases them to the screen at a readable pace. The world and the HUD both read the
 * states built here by their reducers (`world/reduceEvents`, `hud/state`), one event at a time.
 */
import { create } from "zustand";
import type { Decision, GameEvent, SessionConfig } from "../contract/types";
import { seatNames } from "../hud/format";
import { applyEvent as applyHud, initialHudState, type HudState } from "../hud/state";
import { startEngine, type EngineClient, type LoadProgress } from "../runtime/engineClient";
import { WorkerSession } from "../runtime/workerSession";
import { applyEvent as applyWorld, initialState as initialWorld, type WorldState } from "../world/reduceEvents";
import { holdsBeat } from "./pace";

export interface GameStore {
  /** Engine load progress, shown as the atoll being built. */
  load: LoadProgress;
  /** Set when the engine could not load or a game stopped on an error. */
  trouble: string | null;
  config: SessionConfig | null;
  names: string[];
  /** Every event the engine has sent for this game. */
  log: GameEvent[];
  /** How many of `log` are on screen. */
  shown: number;
  world: WorldState;
  hud: HudState;
  /** The person's decision, released once every earlier event is on screen. */
  decision: Decision | null;
  /** Starts loading the engine. Safe to call more than once. */
  boot: () => void;
  startGame: (config: SessionConfig) => Promise<void>;
  submit: (actionId: number) => void;
  leave: () => void;
  /** After trouble: a fresh worker, and the game (if any) carries on where it stopped. */
  retry: () => Promise<void>;
}

let client: EngineClient | null = null;
let session: WorkerSession | null = null;
let beat: ReturnType<typeof setTimeout> | null = null;
let unsubscribe: Array<() => void> = [];

function readable(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export const useGameStore = create<GameStore>()((set, get) => {
  /** Shows queued events, pausing one beat before each bot or agent move. */
  const pump = (): void => {
    if (beat) return;
    const { log, config } = get();
    if (!config) return;
    let { shown, world, hud } = get();
    const names = get().names;
    while (shown < log.length) {
      const event = log[shown];
      if (holdsBeat(event, config.seats) && !waited.has(event.seq)) {
        waited.add(event.seq);
        set({ shown, world, hud });
        beat = setTimeout(() => {
          beat = null;
          pump();
        }, config.agentDelayMs);
        return;
      }
      world = applyWorld(world, event);
      hud = applyHud(hud, event, names);
      shown += 1;
    }
    set({ shown, world, hud, decision: session?.current() ?? null });
  };
  const waited = new Set<number>();

  const connect = (): EngineClient => {
    client = startEngine();
    const own = client;
    own.subscribe((m) => {
      if (own !== client) return;
      if (m.type === "phase") set({ load: { phase: m.phase, fraction: m.fraction } });
      if (m.type === "error") set({ trouble: m.message });
    });
    return own;
  };

  const clearGame = (): void => {
    if (beat) clearTimeout(beat);
    beat = null;
    waited.clear();
    for (const off of unsubscribe) off();
    unsubscribe = [];
    session?.dispose();
    session = null;
  };

  return {
    load: { phase: "core", fraction: 0 },
    trouble: null,
    config: null,
    names: [],
    log: [],
    shown: 0,
    world: initialWorld(2),
    hud: initialHudState(2),
    decision: null,

    boot: () => {
      if (client) return;
      try {
        connect();
      } catch (error) {
        set({ trouble: readable(error) });
      }
    },

    startGame: async (config) => {
      clearGame();
      get().boot();
      const names = seatNames(config.seats);
      set({
        config,
        names,
        log: [],
        shown: 0,
        world: initialWorld(config.seats.length),
        hud: initialHudState(config.seats.length),
        decision: null,
      });
      if (!client) return;
      const own = new WorkerSession(client);
      session = own;
      unsubscribe = [
        own.onEvent((event) => {
          set((s) => ({ log: [...s.log, event] }));
          pump();
        }),
        own.onDecision(() => pump()),
        own.onError((message) => set({ trouble: message })),
      ];
      try {
        await own.start(config);
      } catch (error) {
        if (session === own) set({ trouble: readable(error) });
      }
      pump();
    },

    submit: (actionId) => {
      const own = session;
      if (!own) return;
      set({ decision: null });
      void own.submit(actionId).then(pump, (error) => set({ trouble: readable(error) }));
    },

    leave: () => {
      clearGame();
      set({ config: null, names: [], log: [], shown: 0, decision: null });
    },

    retry: async () => {
      client?.terminate();
      client = null;
      set({ trouble: null, load: { phase: "core", fraction: 0 } });
      let fresh: EngineClient;
      try {
        fresh = connect();
      } catch (error) {
        set({ trouble: readable(error) });
        return;
      }
      if (!session) return;
      try {
        await session.resume(fresh);
      } catch (error) {
        set({ trouble: readable(error) });
      }
      pump();
    },
  };
});

/**
 * Dev builds: `window.__saltmarketRuntime.crash()` stops the worker to show the error screen,
 * and `.store` is the store itself, for playing games from the console.
 */
if (import.meta.env.DEV && typeof window !== "undefined") {
  (window as unknown as { __saltmarketRuntime: object }).__saltmarketRuntime = {
    crash: () => client?.terminate("The engine worker was stopped from the console."),
    store: useGameStore,
  };
}
