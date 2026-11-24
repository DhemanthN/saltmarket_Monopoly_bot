import { describe, expect, it, vi } from "vitest";
import type { Decision, GameEvent, SessionConfig } from "../contract/types";
import type { EngineClient } from "./engineClient";
import type { FromWorker } from "./protocol";
import { WorkerSession } from "./workerSession";

const config = { seed: 1, seats: ["human", "ppo"], agentDelayMs: 0 } as SessionConfig;

function decision(ids: number[]): Decision {
  return {
    kind: "buy",
    seat: 0,
    turn: 1,
    legal: ids.map((id) => ({ id, label: `a${id}` })),
    space: null,
    price: null,
    debt: null,
    offer: null,
  } as unknown as Decision;
}

function ev(seq: number): GameEvent {
  return { turn: 0, seq, t: "roll", seat: 0, dice: [1, 2] } as GameEvent;
}

function fakeClient() {
  const listeners = new Set<(m: FromWorker) => void>();
  const emit = (m: FromWorker) => [...listeners].forEach((l) => l(m));
  const mock = {
    ready: Promise.resolve(),
    subscribe: vi.fn((l: (m: FromWorker) => void) => {
      listeners.add(l);
      return () => listeners.delete(l);
    }),
    play: vi.fn(),
    answer: vi.fn(),
    abort: vi.fn(),
  };
  return { client: mock as unknown as EngineClient, mock, emit };
}

describe("WorkerSession", () => {
  it("rejects illegal ids without waking the worker", async () => {
    const { client, mock, emit } = fakeClient();
    const session = new WorkerSession(client);
    mock.play.mockImplementation(() => emit({ type: "decision", decision: decision([0, 1]) }));
    await session.start(config);
    expect(await session.submit(7)).toEqual({ ok: false, reason: "illegal" });
    expect(mock.answer).not.toHaveBeenCalled();
    expect(session.current()).not.toBeNull();
  });

  it("says not_your_turn when no decision is pending", async () => {
    const { client, mock, emit } = fakeClient();
    const session = new WorkerSession(client);
    mock.play.mockImplementation(() => emit({ type: "decision", decision: decision([0]) }));
    await session.start(config);
    // The worker takes the answer and is still thinking: no new decision yet.
    const first = session.submit(0);
    expect(await session.submit(0)).toEqual({ ok: false, reason: "not_your_turn" });
    emit({ type: "decision", decision: decision([0]) });
    await first;
  });

  it("says game_over after done", async () => {
    const { client, mock, emit } = fakeClient();
    const session = new WorkerSession(client);
    mock.play.mockImplementation(() => emit({ type: "decision", decision: decision([0]) }));
    await session.start(config);
    mock.answer.mockImplementation(() => emit({ type: "done", summary: { fingerprint: "abc" } as never }));
    expect(await session.submit(0)).toEqual({ ok: true, reason: null });
    expect(session.fingerprint()).toBe("abc");
    expect(await session.submit(0)).toEqual({ ok: false, reason: "game_over" });
  });

  it("resume replays stored answers and does not duplicate events", async () => {
    const first = fakeClient();
    const session = new WorkerSession(first.client);
    first.mock.play.mockImplementation(() => {
      first.emit({ type: "events", events: [ev(0), ev(1)] });
      first.emit({ type: "decision", decision: decision([0, 1]) });
    });
    await session.start(config);
    first.mock.answer.mockImplementation(() => {
      first.emit({ type: "events", events: [ev(2)] });
      first.emit({ type: "error", message: "boom" });
    });
    await expect(session.submit(1)).rejects.toThrow("boom");
    expect(session.events()).toHaveLength(3);

    const second = fakeClient();
    second.mock.play.mockImplementation(() => {
      second.emit({ type: "events", events: [ev(0), ev(1), ev(2), ev(3)] });
      second.emit({ type: "decision", decision: decision([0]) });
    });
    await session.resume(second.client);
    expect(second.mock.play).toHaveBeenCalledWith(config, [1]);
    expect(session.events().map((e) => e.seq)).toEqual([0, 1, 2, 3]);
    expect(session.error()).toBeNull();
  });
});
