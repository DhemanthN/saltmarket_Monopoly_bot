import { CylinderGeometry, DodecahedronGeometry, Matrix4, Vector3, type BufferGeometry } from "three";
import { RING_RADIUS, ringPosition } from "./board";
import { box, part, post } from "./geometry";
import { BRIG_ROCK, MARKET_RADIUS } from "./layout";

/*
 * Skyline pieces that belong to no lot: watchtowers on shore cliffs, wooden cranes by the ferry
 * quays, and rope bridges (shore to cliff, and market to the Brig rock). Built in world space
 * and merged into the landmark mesh, so they add no draw calls.
 */

/** Board positions (fractional space index) of the four cliff watchtowers, between lots. */
export const WATCHTOWER_SLOTS = [2.5, 12.5, 22.5, 32.5] as const;
/** Ferry spaces get a quay crane on the shore behind them. */
export const CRANE_SLOTS = [5, 19, 30] as const;
const CLIFF_RADIUS = RING_RADIUS + 4.6;
const SHORE_RADIUS = RING_RADIUS + 3.3;
const CRANE_RADIUS = RING_RADIUS + 3.0;

type Flag = { at: Vector3; rotY: number };

const at = (slot: number, radius: number) => {
  const { angle } = ringPosition(slot);
  return new Vector3(Math.cos(angle) * radius, 0, Math.sin(angle) * radius);
};
const facing = (slot: number) => {
  const { angle } = ringPosition(slot);
  return Math.atan2(-Math.cos(angle), -Math.sin(angle));
};
const place = (g: BufferGeometry, pos: Vector3, rotY: number) => g.applyMatrix4(new Matrix4().makeRotationY(rotY).setPosition(pos));

function watchtower(slot: number, flags: Flag[]): BufferGeometry[] {
  const pos = at(slot, CLIFF_RADIUS);
  const rotY = facing(slot);
  const local: BufferGeometry[] = [
    part(new DodecahedronGeometry(1.0, 0).scale(1.1, 0.9, 1), "world.basalt", { at: [0, 0.2, 0] }),
    part(new CylinderGeometry(0.32, 0.4, 1.4, 8).translate(0, 0.7, 0), "paperDeep", { at: [0, 0.8, 0] }),
    part(new CylinderGeometry(0.42, 0.42, 0.1, 8), "district.driftwood", { at: [0, 2.2, 0] }),
    ...[0, 1, 2, 3].map((i) => part(box(0.12, 0.14, 0.12), "paperDeep", { at: [Math.cos((i * Math.PI) / 2) * 0.34, 2.3, Math.sin((i * Math.PI) / 2) * 0.34] })),
    part(box(0.1, 0.12, 0.1), "world.glow", { at: [0, 2.3, 0] }),
    part(post(0.02, 0.6), "ink", { at: [0, 2.3, 0] }),
  ];
  flags.push({ at: new Vector3(0, 2.86, 0).applyMatrix4(new Matrix4().makeRotationY(rotY).setPosition(pos)), rotY });
  return local.map((g) => place(g, pos, rotY));
}

function crane(slot: number): BufferGeometry[] {
  const pos = at(slot, CRANE_RADIUS);
  const rotY = facing(slot);
  return [
    part(box(0.36, 0.08, 0.36), "district.driftwood"),
    part(box(0.07, 1.4, 0.07), "district.driftwood", { at: [0, 0.08, 0] }),
    part(box(0.05, 0.05, 1.2), "district.driftwood", { at: [0, 1.4, -0.35], rot: [0.12, 0, 0] }),
    part(box(0.012, 0.5, 0.012), "inkSoft", { at: [0, 0.98, -0.88] }),
    part(box(0.16, 0.1, 0.16), "paperDeep", { at: [0, 0.88, -0.88] }),
  ].map((g) => place(g, pos, rotY));
}

/** Planks and two hand ropes between `a` and `b`, sagging `sag` at the middle. */
export function ropeBridge(a: Vector3, b: Vector3, height: number, sag: number, planks = 9): BufferGeometry[] {
  const parts: BufferGeometry[] = [];
  const dir = new Vector3().subVectors(b, a);
  const len = dir.length();
  const rotY = Math.atan2(dir.x, dir.z);
  const step = len / planks;
  const y = (t: number) => height - sag * 4 * t * (1 - t);
  for (let i = 0; i < planks; i += 1) {
    const t = (i + 0.5) / planks;
    const p = new Vector3().lerpVectors(a, b, t);
    parts.push(place(part(box(0.42, 0.03, step * 0.75), "district.driftwood", { at: [0, y(t), 0] }), p, rotY));
    for (const side of [-0.22, 0.22]) {
      parts.push(place(part(box(0.015, 0.015, step * 1.02), "world.road", { at: [side, y(t) + 0.26, 0] }), p, rotY));
    }
  }
  for (const end of [a, b]) for (const side of [-0.22, 0.22]) parts.push(place(part(post(0.025, height + 0.3), "district.driftwood", { at: [side, 0, 0] }), end, rotY));
  return parts;
}

/** All silhouette parts in world space, and the flags they carry. */
export function silhouetteParts(): { parts: BufferGeometry[]; flags: Flag[] } {
  const flags: Flag[] = [];
  const parts: BufferGeometry[] = [];
  for (const slot of WATCHTOWER_SLOTS) parts.push(...watchtower(slot, flags));
  for (const slot of CRANE_SLOTS) parts.push(...crane(slot));
  // Shore to the first two cliffs, and the market square to the Brig rock across the lagoon.
  for (const slot of WATCHTOWER_SLOTS.slice(0, 2)) parts.push(...ropeBridge(at(slot, SHORE_RADIUS), at(slot, CLIFF_RADIUS - 0.8), 0.25, 0.12, 6));
  const marketEdge = new Vector3(BRIG_ROCK.x, 0, BRIG_ROCK.z).setLength(MARKET_RADIUS + 0.1);
  const rockEdge = new Vector3(BRIG_ROCK.x, 0, BRIG_ROCK.z).setLength(new Vector3(BRIG_ROCK.x, 0, BRIG_ROCK.z).length() - 0.9);
  parts.push(...ropeBridge(marketEdge, rockEdge, 0.22, 0.1, 7));
  return { parts, flags };
}
