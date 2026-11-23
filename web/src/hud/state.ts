import boardData from "../../../data/board.json";
import type { GameEvent } from "../contract/types";
import { money, spaceName } from "./format";

/** Starting cash from `src/saltmarket/engine/config.py`. */
export const STARTING_CASH = 1400;

interface RawSpace {
  price?: number;
  mortgage?: number;
  build_cost?: number;
}

const RAW = boardData.spaces as RawSpace[];

export interface FeedLine {
  seq: number;
  text: string;
}

export interface HudState {
  cash: number[];
  /** Change in cash caused by the most recent event that touched each seat. */
  lastDelta: number[];
  owner: (number | null)[];
  level: number[];
  mortgaged: boolean[];
  bankrupt: boolean[];
  feed: FeedLine[];
  /** The auction in progress, with the highest bid so far. */
  auction: { space: number; high: { seat: number; amount: number } | null } | null;
  winner: number | null;
  turns: number | null;
  turn: number;
}

const FEED_LIMIT = 8;

export function initialHudState(seatCount: number): HudState {
  return {
    cash: Array.from({ length: seatCount }, () => STARTING_CASH),
    lastDelta: Array.from({ length: seatCount }, () => 0),
    owner: RAW.map(() => null),
    level: RAW.map(() => 0),
    mortgaged: RAW.map(() => false),
    bankrupt: Array.from({ length: seatCount }, () => false),
    feed: [],
    auction: null,
    winner: null,
    turns: null,
    turn: 0,
  };
}

/** Same formula as `engine/rules.net_worth`: cash, spaces at face value (mortgage value if mortgaged), buildings at cost. */
export function netWorth(state: HudState, seat: number): number {
  if (state.bankrupt[seat]) return 0;
  let total = state.cash[seat];
  state.owner.forEach((owner, i) => {
    if (owner !== seat) return;
    const raw = RAW[i];
    total += state.mortgaged[i] ? (raw.mortgage ?? 0) : (raw.price ?? 0);
    total += state.level[i] * (raw.build_cost ?? 0);
  });
  return total;
}

function pushFeed(state: HudState, seq: number, text: string): void {
  state.feed = [{ seq, text }, ...state.feed].slice(0, FEED_LIMIT);
}

/** Applies one event and returns the next state. `names` gives each seat's display name for the feed. */
export function applyEvent(prev: HudState, event: GameEvent, names: readonly string[]): HudState {
  const state: HudState = {
    ...prev,
    cash: [...prev.cash],
    lastDelta: [...prev.lastDelta],
    owner: [...prev.owner],
    level: [...prev.level],
    mortgaged: [...prev.mortgaged],
    bankrupt: [...prev.bankrupt],
    turn: event.turn,
  };
  switch (event.t) {
    case "cash":
      state.cash[event.seat] = event.balance;
      state.lastDelta[event.seat] = event.delta;
      break;
    case "owner":
      state.owner[event.space] = event.seat;
      break;
    case "build":
    case "sell":
      state.level[event.space] = event.level;
      break;
    case "mortgage":
    case "unmortgage":
      state.mortgaged[event.space] = event.t === "mortgage";
      break;
    case "bankrupt":
      state.bankrupt[event.seat] = true;
      pushFeed(state, event.seq, `${names[event.seat]} went bankrupt`);
      break;
    case "rent":
      pushFeed(
        state,
        event.seq,
        `${names[event.payer]} paid ${money(event.amount)} rent to ${names[event.payee]} at ${spaceName(event.space)}`,
      );
      break;
    case "buy":
      pushFeed(state, event.seq, `${names[event.seat]} bought ${spaceName(event.space)} for ${money(event.price)}`);
      break;
    case "auction_start":
      state.auction = { space: event.space, high: null };
      break;
    case "auction_bid":
      if (state.auction) state.auction = { ...state.auction, high: { seat: event.seat, amount: event.amount } };
      break;
    case "auction_win":
      state.auction = null;
      pushFeed(
        state,
        event.seq,
        event.seat === null
          ? `No bids for ${spaceName(event.space)}`
          : `${names[event.seat]} won ${spaceName(event.space)} at auction for ${money(event.amount)}`,
      );
      break;
    case "trade_result":
      pushFeed(state, event.seq, event.accepted ? "A trade was accepted" : "A trade was declined");
      break;
    case "game_over":
      state.winner = event.winner;
      state.turns = event.turns;
      break;
    default:
      break;
  }
  return state;
}

export function reduceHud(events: readonly GameEvent[], names: readonly string[]): HudState {
  return events.reduce((s, e) => applyEvent(s, e, names), initialHudState(names.length));
}
