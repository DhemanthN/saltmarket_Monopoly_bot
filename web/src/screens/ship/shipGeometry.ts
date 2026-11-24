import {
  BoxGeometry,
  BufferGeometry,
  Color,
  ConeGeometry,
  CylinderGeometry,
  Euler,
  Float32BufferAttribute,
  Matrix4,
  PlaneGeometry,
  Quaternion,
  SphereGeometry,
  Vector3,
} from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";

/*
 * The start-screen pirate ship, built from code: about 3,000 triangles, no download.
 * Bow points toward +x, deck near y = 0.5, length about 8 units. Parts are painted with
 * vertex colours and merged, so the whole ship is three draw calls.
 */

export const SHIP_LENGTH = 8;
export const SHIP_HEIGHT = 6.8;

const WOOD = "#7A5A3C";
const WOOD_DARK = "#4E3822";
const SAIL = "#FBF7EE";
const SAIL_SHADE = "#E6D8BC";
const BRASS = "#C9A24A";
const INK = "#1F2A2E";
const BAND = "#B8321A";

interface Placement {
  at?: [number, number, number];
  rot?: [number, number, number];
}

function part(source: BufferGeometry, color: string, { at = [0, 0, 0], rot = [0, 0, 0] }: Placement = {}): BufferGeometry {
  const g = source.index ? source.toNonIndexed() : source;
  g.deleteAttribute("uv");
  const c = new Color(color);
  const colors: number[] = [];
  for (let i = 0; i < g.getAttribute("position").count; i += 1) colors.push(c.r, c.g, c.b);
  g.setAttribute("color", new Float32BufferAttribute(colors, 3));
  g.applyMatrix4(
    new Matrix4().compose(new Vector3(...at), new Quaternion().setFromEuler(new Euler(...rot)), new Vector3(1, 1, 1)),
  );
  return g;
}

function merge(parts: BufferGeometry[]): BufferGeometry {
  const merged = mergeGeometries(parts);
  if (!merged) throw new Error("Ship parts do not share attributes");
  merged.computeVertexNormals();
  merged.computeBoundingSphere();
  return merged;
}

/** Half-breadth, keel depth and gunwale rise at t along the keel (0 stern, 1 bow). */
function hullProfile(t: number): { half: number; deep: number; rise: number } {
  const half = 0.25 + 1.0 * Math.sin(Math.PI * Math.pow(t, 0.7)) * Math.pow(1 - t * 0.55, 0.8);
  const deep = 0.95 - 0.55 * Math.pow(t, 2.4);
  const rise = 0.55 * Math.pow(t, 3) + 0.25 * Math.pow(1 - t, 3);
  return { half: Math.min(half, 1.25), deep, rise };
}

/** Point on a hull rib: `u` runs 0 at the keel to 1 at the gunwale. */
function ribPoint(t: number, u: number, side: 1 | -1, lift = 0): [number, number, number] {
  const { half, deep, rise } = hullProfile(t);
  const w = half * Math.sin((Math.PI / 2) * Math.min(1, u * 1.15 + 0.02)) + lift;
  const y = -deep * (1 - u) * (1 - u * 0.35) + rise * u;
  return [-SHIP_LENGTH / 2 + t * SHIP_LENGTH, y, w * side];
}

/** A lofted strip between ribs `u0` and `u1` on one side, wound so its normal faces outward. */
function loft(stations: number, ribs: number, point: (t: number, u: number) => [number, number, number], side: 1 | -1) {
  const positions: number[] = [];
  const index: number[] = [];
  for (let s = 0; s <= stations; s += 1) {
    for (let r = 0; r <= ribs; r += 1) positions.push(...point(s / stations, r / ribs));
  }
  for (let s = 0; s < stations; s += 1) {
    for (let r = 0; r < ribs; r += 1) {
      const a = s * (ribs + 1) + r;
      const c = a + ribs + 1;
      if (side === 1) index.push(a, c, a + 1, a + 1, c, c + 1);
      else index.push(a, a + 1, c, a + 1, c + 1, c);
    }
  }
  const g = new BufferGeometry();
  g.setAttribute("position", new Float32BufferAttribute(positions, 3));
  g.setIndex(index);
  return g;
}

/** The hull shell plus a red painted wale along each side. */
function hull(): BufferGeometry {
  const parts: BufferGeometry[] = [];
  for (const side of [1, -1] as const) {
    parts.push(part(loft(14, 6, (t, u) => ribPoint(t, u, side), side), WOOD));
    parts.push(part(loft(10, 1, (t, u) => ribPoint(0.04 + t * 0.92, 0.55 + u * 0.1, side, 0.012), side), BAND));
  }
  return merge(parts);
}

const cyl = (r: number, h: number, seg = 6) => new CylinderGeometry(r, r, h, seg);
const box = (w: number, h: number, d: number) => new BoxGeometry(w, h, d);

/** A sail bellied out toward +z, the camera side. */
function sail(width: number, height: number, belly: number, color: string): BufferGeometry {
  const g = new PlaneGeometry(width, height, 6, 5);
  const p = g.getAttribute("position");
  for (let i = 0; i < p.count; i += 1) {
    const nx = p.getX(i) / (width / 2);
    const ny = p.getY(i) / (height / 2);
    p.setZ(i, belly * (1 - nx * nx) * (1 - ny * ny * 0.6));
  }
  return part(g, color);
}

interface MastSpec {
  x: number;
  height: number;
  lower: number;
  upper: number;
  width: number;
}

const MASTS: readonly MastSpec[] = [
  { x: 2.2, height: 4.6, lower: 1.9, upper: 1.2, width: 2.5 },
  { x: 0.1, height: 5.9, lower: 2.4, upper: 1.6, width: 3.1 },
  { x: -2.0, height: 4.7, lower: 1.9, upper: 1.2, width: 2.5 },
];

function stick(a: Vector3, b: Vector3): BufferGeometry {
  const dir = b.clone().sub(a);
  const mid = a.clone().add(b).multiplyScalar(0.5);
  const q = new Quaternion().setFromUnitVectors(new Vector3(0, 1, 0), dir.clone().normalize());
  const e = new Euler().setFromQuaternion(q);
  return part(cyl(0.014, dir.length(), 3), INK, { at: [mid.x, mid.y, mid.z], rot: [e.x, e.y, e.z] });
}

/** Wood and metal: decks, castles, masts, yards, bowsprit, rigging, cannons, lanterns, wheel. */
function timber(): BufferGeometry {
  const parts: BufferGeometry[] = [
    part(box(SHIP_LENGTH * 0.72, 0.05, 1.7), WOOD_DARK, { at: [0.1, 0.5, 0] }),
    part(box(1.7, 0.55, 2.0), WOOD, { at: [-2.9, 0.78, 0] }),
    part(box(1.8, 0.07, 2.1), WOOD_DARK, { at: [-2.9, 1.08, 0] }),
    part(box(1.0, 0.4, 1.6), WOOD, { at: [3.0, 0.7, 0] }),
    part(cyl(0.05, 2.2, 5), WOOD_DARK, { at: [4.6, 0.9, 0], rot: [0, 0, -1.2] }),
    part(cyl(0.3, 0.05, 12), WOOD_DARK, { at: [-2.4, 1.3, 0], rot: [Math.PI / 2, 0, 0] }),
  ];
  for (const m of MASTS) {
    parts.push(part(cyl(0.09, m.height, 7), WOOD_DARK, { at: [m.x, 0.5 + m.height / 2, 0] }));
    parts.push(part(new SphereGeometry(0.12, 8, 6), BRASS, { at: [m.x, 0.5 + m.height + 0.05, 0] }));
    const lowY = 0.5 + m.height * 0.38 + m.lower;
    const upY = 0.5 + m.height - 0.25;
    parts.push(part(cyl(0.05, m.width + 0.4, 5), WOOD_DARK, { at: [m.x, lowY + 0.05, 0], rot: [0, 0, Math.PI / 2] }));
    parts.push(part(cyl(0.04, m.width * 0.7, 5), WOOD_DARK, { at: [m.x, upY, 0], rot: [0, 0, Math.PI / 2] }));
    parts.push(part(box(0.38, 0.28, 0.38), WOOD_DARK, { at: [m.x, 0.5 + m.height * 0.62, 0] }));
    for (const z of [0.9, -0.9]) {
      parts.push(stick(new Vector3(m.x, 0.5 + m.height - 0.3, 0), new Vector3(m.x + 0.5, 0.55, z)));
      parts.push(stick(new Vector3(m.x, 0.5 + m.height - 0.3, 0), new Vector3(m.x - 0.5, 0.55, z)));
    }
  }
  for (const z of [1, -1]) {
    for (const x of [-1.1, -0.2, 0.7, 1.6]) {
      parts.push(part(cyl(0.09, 0.55, 6), INK, { at: [x, 0.3, z * 1.1], rot: [Math.PI / 2, 0, 0] }));
      parts.push(part(new SphereGeometry(0.1, 6, 4), BRASS, { at: [x, 0.3, z * 1.4] }));
    }
    parts.push(part(box(0.18, 0.28, 0.18), BRASS, { at: [-3.75, 1.3, z * 0.85] }));
    parts.push(part(new ConeGeometry(0.14, 0.14, 4), INK, { at: [-3.75, 1.5, z * 0.85] }));
  }
  return merge(parts);
}

/** Sails and the black flag with its pale skull. */
function canvas(): BufferGeometry {
  const parts: BufferGeometry[] = [];
  MASTS.forEach((m, i) => {
    const lowY = 0.5 + m.height * 0.38 + m.lower;
    parts.push(sail(m.width, m.lower * 1.5, 0.45, SAIL).translate(m.x, lowY - (m.lower * 1.5) / 2, 0.05));
    const upper = sail(m.width * 0.72, m.upper * 1.2, 0.35, i === 1 ? SAIL : SAIL_SHADE);
    parts.push(upper.translate(m.x, 0.5 + m.height - 0.2 - (m.upper * 1.2) / 2, 0.05));
  });
  const flagY = 0.5 + MASTS[1].height + 0.45;
  parts.push(part(new PlaneGeometry(1.0, 0.6, 4, 2), INK, { at: [0.1 + 0.55, flagY, 0] }));
  parts.push(part(new SphereGeometry(0.11, 8, 6), SAIL, { at: [0.1 + 0.55, flagY, 0.02] }));
  return merge(parts);
}

export interface ShipGeometry {
  hull: BufferGeometry;
  timber: BufferGeometry;
  canvas: BufferGeometry;
}

/** The ship's three merged meshes: painted hull, timber and metal, canvas. */
export function buildShipGeometry(): ShipGeometry {
  return { hull: hull(), timber: timber(), canvas: canvas() };
}

/** Triangles across the three meshes, so a test can hold the ship near its 3k budget. */
export function triangleCount(geometry: ShipGeometry): number {
  return Object.values(geometry).reduce(
    (sum, g) => sum + (g.index ? g.index.count : g.getAttribute("position").count) / 3,
    0,
  );
}
