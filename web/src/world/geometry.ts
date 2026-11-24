import {
  BoxGeometry,
  BufferGeometry,
  ConeGeometry,
  CylinderGeometry,
  ExtrudeGeometry,
  Matrix4,
  Euler,
  Quaternion,
  Shape,
  SphereGeometry,
  Vector3,
} from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import type { DistrictName } from "../styles/tokens";
import { paint } from "./palette";

/*
 * Procedural lot geometry. Every building is built in lot space: origin at ground centre,
 * +z faces the road, footprint about 1.1 x 1.1. Each part is painted into one palette cell
 * and the parts are merged, so one district type is one draw call when instanced.
 */

interface Placement {
  at?: [number, number, number];
  rot?: [number, number, number];
}

function part(geometry: BufferGeometry, cell: string, { at = [0, 0, 0], rot = [0, 0, 0] }: Placement = {}): BufferGeometry {
  const g = geometry.index ? geometry.toNonIndexed() : geometry;
  paint(g, cell);
  const m = new Matrix4().compose(new Vector3(...at), new Quaternion().setFromEuler(new Euler(...rot)), new Vector3(1, 1, 1));
  g.applyMatrix4(m);
  return g;
}

function merge(parts: BufferGeometry[]): BufferGeometry {
  const merged = mergeGeometries(parts);
  if (!merged) throw new Error("Lot geometry parts do not share attributes");
  merged.computeBoundingSphere();
  return merged;
}

/** A gabled prism (A-frame or roof): width along x, height up, depth along z, base at y = 0. */
function prism(width: number, height: number, depth: number): BufferGeometry {
  const s = new Shape();
  s.moveTo(-width / 2, 0);
  s.lineTo(width / 2, 0);
  s.lineTo(0, height);
  s.closePath();
  const g = new ExtrudeGeometry(s, { depth, bevelEnabled: false });
  g.translate(0, 0, -depth / 2);
  return g;
}

const box = (w: number, h: number, d: number, y = 0) => new BoxGeometry(w, h, d).translate(0, h / 2 + y, 0);
const post = (r: number, h: number) => new CylinderGeometry(r, r, h, 5).translate(0, h / 2, 0);

function districtBase(name: DistrictName): BufferGeometry {
  const accent = `district.${name}`;
  switch (name) {
    case "kelp": // low stilt shacks with drying racks over the shallows, wide and flat
      return merge([
        ...[-0.45, 0.45].flatMap((x) => [-0.35, 0.35].map((z) => part(post(0.04, 0.3), "district.driftwood", { at: [x, 0, z] }))),
        part(box(1.1, 0.06, 0.9), "paperDeep", { at: [0, 0.3, 0] }),
        part(box(0.7, 0.26, 0.5), "paper", { at: [-0.1, 0.36, -0.1] }),
        part(box(0.8, 0.04, 0.6), accent, { at: [-0.1, 0.62, -0.1] }),
        part(post(0.02, 0.35), "inkSoft", { at: [0.42, 0.36, 0.3] }),
        part(post(0.02, 0.35), "inkSoft", { at: [0.42, 0.36, -0.3] }),
        part(box(0.03, 0.12, 0.6), accent, { at: [0.42, 0.55, 0] }),
      ]);
    case "reef": // squat round stone towers behind a sea wall
      return merge([
        part(box(1.1, 0.28, 0.14), "paperDeep", { at: [0, 0, 0.42] }),
        part(new CylinderGeometry(0.26, 0.3, 0.8, 8).translate(0, 0.4, 0), "paper", { at: [-0.28, 0, -0.1] }),
        part(new CylinderGeometry(0.22, 0.26, 0.62, 8).translate(0, 0.31, 0), "paper", { at: [0.3, 0, -0.15] }),
        part(new CylinderGeometry(0.3, 0.3, 0.08, 8), accent, { at: [-0.28, 0.82, -0.1] }),
        part(new CylinderGeometry(0.26, 0.26, 0.08, 8), accent, { at: [0.3, 0.64, -0.15] }),
      ]);
    case "coral": // stepped terraces with rounded domes
      return merge([
        part(box(1.0, 0.3, 0.9), "paper"),
        part(box(0.74, 0.3, 0.64), "sailcloth", { at: [0, 0.3, -0.08] }),
        part(box(0.48, 0.26, 0.4), "paper", { at: [0, 0.6, -0.14] }),
        part(new SphereGeometry(0.2, 10, 6, 0, Math.PI * 2, 0, Math.PI / 2), accent, { at: [0, 0.86, -0.14] }),
        part(new SphereGeometry(0.12, 8, 5, 0, Math.PI * 2, 0, Math.PI / 2), accent, { at: [0.36, 0.3, 0.2] }),
      ]);
    case "driftwood": // leaning timber A-frames, deliberately crooked
      return merge([
        part(prism(0.7, 0.85, 0.6), accent, { at: [-0.2, 0, -0.05], rot: [0, 0.2, 0.14] }),
        part(prism(0.5, 0.6, 0.45), "district.driftwood", { at: [0.32, 0, 0.12], rot: [0, -0.35, -0.18] }),
        part(box(0.2, 0.3, 0.04), "ink", { at: [-0.2, 0, 0.27] }),
      ]);
    case "amber": // glasshouse workshops whose roofs glow at dusk
      return merge([
        part(box(0.95, 0.34, 0.7), "paper"),
        part(prism(0.95, 0.4, 0.7), accent, { at: [0, 0.34, 0] }),
        part(box(0.3, 0.5, 0.3), "paperDeep", { at: [0.36, 0, -0.3] }),
      ]);
    case "cinder": // dark basalt foundries with chimneys and smoke, the sharpest spikes
      return merge([
        part(box(0.95, 0.62, 0.72), "world.basalt"),
        part(prism(0.95, 0.3, 0.72), accent, { at: [0, 0.62, 0] }),
        part(new CylinderGeometry(0.07, 0.1, 1.6, 6).translate(0, 0.8, 0), "world.basalt", { at: [-0.3, 0, -0.22] }),
        part(new CylinderGeometry(0.05, 0.08, 1.25, 6).translate(0, 0.62, 0), "world.basalt", { at: [0.28, 0, -0.25] }),
        part(new ConeGeometry(0.1, 0.4, 4).translate(0, 0.2, 0), "danger", { at: [0, 0.92, 0.1] }),
      ]);
    case "jade": // steep verdigris-roofed merchant halls
      return merge([
        part(box(0.85, 0.6, 0.62), "paper"),
        part(prism(0.92, 0.7, 0.68), accent, { at: [0, 0.6, 0] }),
        part(box(0.18, 0.28, 0.04), "ink", { at: [0, 0, 0.32] }),
      ]);
    case "crown": // harbour-master towers with flag masts, the highest skyline
      return merge([
        part(box(0.95, 0.3, 0.7), "paper"),
        part(box(0.42, 1.55, 0.42), "sailcloth", { at: [-0.18, 0, -0.1] }),
        part(new ConeGeometry(0.34, 0.45, 4).rotateY(Math.PI / 4).translate(0, 0.22, 0), accent, { at: [-0.18, 1.55, -0.1] }),
        part(post(0.02, 0.6), "ink", { at: [-0.18, 2.0, -0.1] }),
        part(box(0.26, 0.14, 0.02), accent, { at: [-0.05, 2.42, -0.1] }),
      ]);
  }
}

/** Height of one storey added by a build. */
export const STOREY_HEIGHT = 0.2;

/** Where the storey stack stands in lot space, beside the district building. */
export const STOREY_ANCHOR: [number, number, number] = [0.38, 0, -0.32];

function districtStorey(name: DistrictName): BufferGeometry {
  return merge([
    part(box(0.32, STOREY_HEIGHT * 0.8, 0.32), "sailcloth"),
    part(box(0.34, STOREY_HEIGHT * 0.2, 0.34, STOREY_HEIGHT * 0.8), `district.${name}`),
  ]);
}

/** Merged base geometry per district, built once. */
export function buildDistrictGeometry(name: DistrictName): { base: BufferGeometry; storey: BufferGeometry } {
  return { base: districtBase(name), storey: districtStorey(name) };
}

/** Owner awning: samples the white cell so the instance colour shows the owner. */
export function awningGeometry(): BufferGeometry {
  return merge([part(box(0.6, 0.03, 0.26), "world.white", { at: [0, 0, 0], rot: [0.35, 0, 0] })]);
}

/** Closed shutters, shown only on mortgaged lots: paper-deep slats on an ink frame. */
export function shutterGeometry(): BufferGeometry {
  return merge([
    part(box(0.56, 0.24, 0.03), "ink"),
    ...[0.02, 0.1, 0.18].map((y) => part(box(0.5, 0.06, 0.02), "paperDeep", { at: [0, y, 0.02] })),
  ]);
}

/** Port: a crane and a quay slab, added at `PORT_LEVEL`. */
export function portGeometry(): BufferGeometry {
  return merge([
    part(box(1.15, 0.06, 0.35), "paperDeep", { at: [0, 0, 0.55] }),
    part(post(0.03, 0.9), "brass", { at: [0.45, 0, 0.55] }),
    part(box(0.55, 0.04, 0.04), "brass", { at: [0.25, 0.86, 0.55] }),
  ]);
}

/** Marker for non-property spaces (start, cards, tax, ferry, utility, rest). */
export function markerGeometry(): BufferGeometry {
  return merge([part(box(0.5, 0.08, 0.5), "paperDeep"), part(post(0.035, 0.55), "brass", { at: [0, 0.08, 0] }), part(box(0.34, 0.2, 0.03), "sailcloth", { at: [0, 0.4, 0] })]);
}

/** One piece: a pawn body sampling the white cell (instance colour = seat) with an ink collar. */
export function pieceGeometry(): BufferGeometry {
  return merge([
    part(new CylinderGeometry(0.22, 0.26, 0.1, 10).translate(0, 0.05, 0), "world.white"),
    part(new CylinderGeometry(0.09, 0.18, 0.42, 10).translate(0, 0.31, 0), "world.white"),
    part(new SphereGeometry(0.13, 10, 8).translate(0, 0.6, 0), "world.white"),
  ]);
}
