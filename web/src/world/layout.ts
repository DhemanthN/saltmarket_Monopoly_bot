import { Vector3 } from "three";
import { RING_RADIUS, ringPosition } from "./board";

/*
 * Where things stand on the atoll. Pieces walk the road on the ring; lots sit just outside it;
 * the market square, the Brig rock and the seat harbours are in the lagoon.
 */

export const LOT_RADIUS = RING_RADIUS + 1.45;
export const ROAD_WIDTH = 1.5;
export const LAGOON_RADIUS = RING_RADIUS - 1.6;
export const MARKET_RADIUS = 1.6;
export const BRIG_ROCK = new Vector3(-3.4, 0.35, 2.2);
export const HARBOUR_RADIUS = 3.6;

/** Lot centre and the y rotation that turns lot-space +z toward the road. */
export function lotTransform(index: number): { x: number; z: number; rotY: number } {
  const { angle } = ringPosition(index);
  return {
    x: Math.cos(angle) * LOT_RADIUS,
    z: Math.sin(angle) * LOT_RADIUS,
    rotY: Math.atan2(-Math.cos(angle), -Math.sin(angle)),
  };
}

/** Where a seat's piece stands on a space: on the road, spread across its width. */
export function pieceSpot(space: number, seat: number, seatCount: number, out = new Vector3()): Vector3 {
  const { angle } = ringPosition(space);
  const spread = seatCount > 1 ? (seat / (seatCount - 1) - 0.5) * (ROAD_WIDTH * 0.6) : 0;
  const r = RING_RADIUS + spread;
  return out.set(Math.cos(angle) * r, 0.05, Math.sin(angle) * r);
}

/** A seat's harbour on the market square's shore, where rent coins land. */
export function harbourSpot(seat: number, out = new Vector3()): Vector3 {
  const a = Math.PI / 4 + (seat * Math.PI) / 2;
  return out.set(Math.cos(a) * HARBOUR_RADIUS, 0.1, Math.sin(a) * HARBOUR_RADIUS);
}

/** Direction of travel along the road at a space (clockwise from above), as a unit vector. */
export function roadForward(space: number, out = new Vector3()): Vector3 {
  const { angle } = ringPosition(space);
  return out.set(Math.sin(angle), 0, -Math.cos(angle));
}
