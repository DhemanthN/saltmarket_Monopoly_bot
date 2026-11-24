/**
 * `GameSession` backed by the engine worker. The worker plays the game once and blocks on each
 * human decision; this class keeps the event log, checks answers before waking the worker, and
 * can move the game to a fresh worker after an error by replaying the answers given so far.
 */
import type {
  Decision,
  GameEvent,
  GameSession,
  SessionConfig,
  SubmitResult,
  Unsubscribe,
} from "../contract/types";
import type { GameSummary } from "./engineCore";
import type { EngineClient } from "./engineClient";
import type { FromWorker } from "./protocol";

type Waiter = { resolve: () => void; reject: (error: Error) => void };

export class WorkerSession implements GameSession {
  private client: EngineClient;
  private config: SessionConfig | null = null;
  private readonly log: GameEvent[] = [];
  private readonly answers: number[] = [];
  private pending: Decision | null = null;
  private summary: GameSummary | null = null;
  private failure: string | null = null;
  private waiter: Waiter | null = null;
  /** Set by `dispose`, so a start or resume still waiting for the engine never plays. */
  private disposed = false;
  private unsubscribeClient: () => void = () => {};
  private readonly eventListeners = new Set<(event: GameEvent) => void>();
  private readonly decisionListeners = new Set<(decision: Decision) => void>();
  private readonly errorListeners = new Set<(message: string) => void>();

  constructor(client: EngineClient) {
    this.client = client;
  }

  async start(config: SessionConfig): Promise<void> {
    this.config = config;
    await this.client.ready;
    if (this.disposed) return;
    await this.run();
  }

  current(): Decision | null {
    return this.pending;
  }

  async submit(action: number): Promise<SubmitResult> {
    if (this.summary) return { ok: false, reason: "game_over" };
    if (!this.pending) return { ok: false, reason: "not_your_turn" };
    if (!this.pending.legal.some((a) => a.id === action)) return { ok: false, reason: "illegal" };
    this.pending = null;
    this.answers.push(action);
    const settled = this.wait();
    this.client.answer(action);
    await settled;
    return { ok: true, reason: null };
  }

  events(sinceIndex = 0): GameEvent[] {
    return this.log.slice(sinceIndex);
  }

  onEvent(callback: (event: GameEvent) => void): Unsubscribe {
    this.eventListeners.add(callback);
    return () => this.eventListeners.delete(callback);
  }

  onDecision(callback: (decision: Decision) => void): Unsubscribe {
    this.decisionListeners.add(callback);
    return () => this.decisionListeners.delete(callback);
  }

  /** Called with a readable message when the worker fails during a game. */
  onError(callback: (message: string) => void): Unsubscribe {
    this.errorListeners.add(callback);
    return () => this.errorListeners.delete(callback);
  }

  fingerprint(): string | null {
    return this.summary?.fingerprint ?? null;
  }

  /** The engine's summary once the game is over. */
  result(): GameSummary | null {
    return this.summary;
  }

  /** The worker error that stopped this game, if any. Cleared by `resume`. */
  error(): string | null {
    return this.failure;
  }

  /** Answers given so far, in order. */
  given(): readonly number[] {
    return this.answers;
  }

  /**
   * Continues on a fresh worker after an error. The game is rebuilt from the seed and the
   * answers given so far; events already in the log are not repeated.
   */
  async resume(client: EngineClient): Promise<void> {
    this.unsubscribeClient();
    this.client = client;
    this.failure = null;
    await client.ready;
    if (this.disposed) return;
    await this.run();
  }

  dispose(): void {
    this.disposed = true;
    this.unsubscribeClient();
    if (!this.summary && !this.failure) this.client.abort();
    this.eventListeners.clear();
    this.decisionListeners.clear();
    this.errorListeners.clear();
  }

  private run(): Promise<void> {
    if (!this.config) throw new Error("Call start() first");
    this.unsubscribeClient = this.client.subscribe((m) => this.handle(m));
    const settled = this.wait();
    this.client.play(this.config, this.answers);
    return settled;
  }

  /** Resolves at the next human decision or the end of the game, rejects on a worker error. */
  private wait(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.waiter = { resolve, reject };
    });
  }

  private settle(error?: Error): void {
    const waiter = this.waiter;
    this.waiter = null;
    if (!waiter) return;
    if (error) waiter.reject(error);
    else waiter.resolve();
  }

  private handle(message: FromWorker): void {
    switch (message.type) {
      case "events":
        for (const event of message.events) {
          // A resumed game re-sends the events this session already has.
          if (event.seq < this.log.length) continue;
          this.log.push(event);
          for (const listener of this.eventListeners) listener(event);
        }
        break;
      case "decision":
        this.pending = message.decision;
        for (const listener of this.decisionListeners) listener(message.decision);
        this.settle();
        break;
      case "done":
        this.summary = message.summary;
        this.settle();
        break;
      case "error":
        this.failure = message.message;
        this.pending = null;
        for (const listener of this.errorListeners) listener(message.message);
        this.settle(new Error(message.message));
        break;
      default:
        break;
    }
  }
}
