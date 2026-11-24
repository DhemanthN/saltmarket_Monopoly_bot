import type { GameEvent } from "../contract/types";
import { BRIG_SPACE, spaces } from "./board";

/** Starting cash per seat, from `GameConfig.starting_cash` in the engine. */
export const STARTING_CASH = 1400;

/** The last hop sequence, so the scene can animate it. `seq` changes on every move. */
export interface MoveTrace {
  seq: number;
  seat: number;
  path: number[];
}

/** The last rent payment, so the scene can send a coin cart. */
export interface RentTrace {
  seq: number;
  payer: number;
  payee: number;
  space: number;
  amount: number;
}

/** Everything the 3D world draws. The scene renders this, never events. */
export interface WorldState {
  turn: number;
  /** Number of events folded in so far. */
  applied: number;
  cash: number[];
  owner: (number | null)[];
  level: number[];
  mortgaged: boolean[];
  position: number[];
  inBrig: boolean[];
  bankrupt: boolean[];
  lastMove: MoveTrace | null;
  lastRent: RentTrace | null;
  /** Space under the hammer, or null when no auction runs. */
  auction: number | null;
  winner: number | null;
  /** Bumps whenever lots change (owner, level, mortgage), so shadows refresh only then. */
  boardVersion: number;
}

/** The world before the first event: everyone on Home Quay with starting cash. */
export function initialState(seatCount: number): WorldState {
  const n = spaces.length;
  return {
    turn: 0,
    applied: 0,
    cash: Array<number>(seatCount).fill(STARTING_CASH),
    owner: Array<number | null>(n).fill(null),
    level: Array<number>(n).fill(0),
    mortgaged: Array<boolean>(n).fill(false),
    position: Array<number>(seatCount).fill(0),
    inBrig: Array<boolean>(seatCount).fill(false),
    bankrupt: Array<boolean>(seatCount).fill(false),
    lastMove: null,
    lastRent: null,
    auction: null,
    winner: null,
    boardVersion: 0,
  };
}

function replaced<T>(items: readonly T[], index: number, value: T): T[] {
  const next = items.slice();
  next[index] = value;
  return next;
}

/** Fold one event into the state. Pure: returns a new state and never mutates `state`. */
export function applyEvent(state: WorldState, e: GameEvent): WorldState {
  const s: WorldState = { ...state, turn: e.turn, applied: state.applied + 1 };
  const board = (patch: Partial<WorldState>): WorldState => ({
    ...s,
    ...patch,
    boardVersion: s.boardVersion + 1,
  });
  switch (e.t) {
    case "cash":
      return { ...s, cash: replaced(s.cash, e.seat, e.balance) };
    case "move":
      return {
        ...s,
        position: replaced(s.position, e.seat, e.path[e.path.length - 1] ?? s.position[e.seat]),
        lastMove: { seq: e.seq, seat: e.seat, path: e.path },
      };
    case "brig_in":
      return {
        ...s,
        position: replaced(s.position, e.seat, BRIG_SPACE),
        inBrig: replaced(s.inBrig, e.seat, true),
        lastMove: { seq: e.seq, seat: e.seat, path: [BRIG_SPACE] },
      };
    case "brig_out":
      return { ...s, inBrig: replaced(s.inBrig, e.seat, false) };
    case "owner":
      return board({ owner: replaced(s.owner, e.space, e.seat) });
    case "build":
    case "sell":
      return board({ level: replaced(s.level, e.space, e.level) });
    case "mortgage":
    case "unmortgage":
      return board({ mortgaged: replaced(s.mortgaged, e.space, e.t === "mortgage") });
    case "rent":
      return {
        ...s,
        lastRent: { seq: e.seq, payer: e.payer, payee: e.payee, space: e.space, amount: e.amount },
      };
    case "auction_start":
      return { ...s, auction: e.space };
    case "auction_win":
      return { ...s, auction: null };
    case "bankrupt":
      return { ...s, bankrupt: replaced(s.bankrupt, e.seat, true) };
    case "game_over":
      return { ...s, winner: e.winner };
    default:
      return s;
  }
}

/** State after the first `count` events. */
export function reduceCount(events: readonly GameEvent[], seatCount: number, count: number): WorldState {
  let state = initialState(seatCount);
  for (let i = 0; i < Math.min(count, events.length); i += 1) state = applyEvent(state, events[i]);
  return state;
}

/** State after every event whose turn is at most `turn`. */
export function reduceEvents(events: readonly GameEvent[], turn: number, seatCount: number): WorldState {
  const count = events.findIndex((e) => e.turn > turn);
  return reduceCount(events, seatCount, count === -1 ? events.length : count);
}
