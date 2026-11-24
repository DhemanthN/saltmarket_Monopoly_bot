/** The page's handle on one engine worker: load progress, game messages and the answer cell. */
import type { SessionConfig } from "../contract/types";
import { CELL_ABORT, CELL_ACTION, CELL_COUNT, CELL_FLAG, type FromWorker, type LoadPhase, type ToWorker } from "./protocol";

/** The parts of a `Worker` the client uses, so tests can pass a fake. */
export interface WorkerLike {
  postMessage(message: ToWorker): void;
  terminate(): void;
  onmessage: ((event: MessageEvent<FromWorker>) => void) | null;
  onerror: ((event: ErrorEvent) => void) | null;
}

export interface LoadProgress {
  phase: LoadPhase;
  fraction: number;
}

type Listener = (message: FromWorker) => void;

export class EngineClient {
  private readonly worker: WorkerLike;
  private readonly cell: Int32Array;
  private readonly listeners = new Set<Listener>();
  private lastProgress: LoadProgress = { phase: "core", fraction: 0 };
  private failure: string | null = null;
  /** Resolves when the engine can play, rejects if loading fails. */
  readonly ready: Promise<void>;

  constructor(worker: WorkerLike) {
    this.worker = worker;
    if (typeof SharedArrayBuffer === "undefined") {
      throw new Error("This browser tab is not cross-origin isolated, so the engine cannot pause for your moves.");
    }
    const sab = new SharedArrayBuffer(CELL_COUNT * Int32Array.BYTES_PER_ELEMENT);
    this.cell = new Int32Array(sab);
    this.ready = new Promise((resolve, reject) => {
      this.subscribe((m) => {
        if (m.type === "phase" && m.phase === "ready") resolve();
        if (m.type === "error") reject(new Error(m.message));
      });
    });
    // Callers that never await `ready` must not see an unhandled rejection.
    this.ready.catch(() => {});
    worker.onmessage = ({ data }) => {
      if (data.type === "phase") this.lastProgress = { phase: data.phase, fraction: data.fraction };
      if (data.type === "error") this.failure = data.message;
      for (const listener of [...this.listeners]) listener(data);
    };
    worker.onerror = (event) => {
      event.preventDefault?.();
      const message: FromWorker = { type: "error", message: event.message || "The engine worker stopped" };
      this.failure = message.message;
      for (const listener of [...this.listeners]) listener(message);
    };
    worker.postMessage({ type: "init", sab });
  }

  get progress(): LoadProgress {
    return this.lastProgress;
  }

  /** The last worker error, if any. */
  get error(): string | null {
    return this.failure;
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  play(config: SessionConfig, answers: readonly number[]): void {
    Atomics.store(this.cell, CELL_ABORT, 0);
    Atomics.store(this.cell, CELL_FLAG, 0);
    this.worker.postMessage({ type: "play", config, answers: [...answers] });
  }

  /** Wakes the worker waiting on a human decision with the chosen action. */
  answer(action: number): void {
    Atomics.store(this.cell, CELL_ACTION, action);
    Atomics.store(this.cell, CELL_FLAG, 1);
    Atomics.notify(this.cell, CELL_FLAG);
  }

  /** Ends a game that is waiting on the person, so the worker can start another. */
  abort(): void {
    Atomics.store(this.cell, CELL_ABORT, 1);
    Atomics.store(this.cell, CELL_FLAG, 1);
    Atomics.notify(this.cell, CELL_FLAG);
  }

  /** Stops the worker for good. Used for retry after an error, and by the dev crash hook. */
  terminate(reason?: string): void {
    this.worker.terminate();
    if (reason) {
      this.failure = reason;
      for (const listener of [...this.listeners]) listener({ type: "error", message: reason });
    }
  }
}

/** Starts a real engine worker. */
export function startEngine(): EngineClient {
  const worker = new Worker(new URL("./engine.worker.ts", import.meta.url), { type: "module" });
  return new EngineClient(worker as unknown as WorkerLike);
}
