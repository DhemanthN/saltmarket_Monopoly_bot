import {
  BoxGeometry,
  BufferGeometry,
  ConeGeometry,
  CylinderGeometry,
  Euler,
  ExtrudeGeometry,
  Matrix4,
  Quaternion,
  Shape,
  SphereGeometry,
  TorusGeometry,
  Vector3,
} from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import type { EmblemName } from "../styles/tokens";
import { nonIndexed, paint } from "./palette";

/*
 * The four carved-and-brass seat pieces: sloop (sun), skull flag (wave), compass (star) and
 * anchor. Wood, brass and iron are painted into palette cells (`body`). The owner colour sits on
 * cloth only (sail, flag, compass face, rope wrap, plinth ring): that part samples the white cell,
 * so the material colour shows the seat. Each piece is two meshes, `body` and `cloth`.
 */

export interface PieceModel {
  body: BufferGeometry;
  cloth: BufferGeometry;
}

interface Placement {
  at?: [number, number, number];
  rot?: [number, number, number];
}

const WOOD = "district.driftwood";
const BRASS = "brass";
const IRON = "inkSoft";
const BONE = "sailcloth";
const CLOTH = "world.white";

function part(geometry: BufferGeometry, cell: string, { at = [0, 0, 0], rot = [0, 0, 0] }: Placement = {}): BufferGeometry {
  const g = nonIndexed(geometry);
  paint(g, cell);
  g.applyMatrix4(new Matrix4().compose(new Vector3(...at), new Quaternion().setFromEuler(new Euler(...rot)), new Vector3(1, 1, 1)));
  return g;
}

function merge(parts: BufferGeometry[]): BufferGeometry {
  const merged = mergeGeometries(parts);
  if (!merged) throw new Error("Piece parts do not share attributes");
  merged.computeBoundingSphere();
  return merged;
}

const cyl = (r: number, h: number, seg = 8) => new CylinderGeometry(r, r, h, seg).translate(0, h / 2, 0);
const box = (w: number, h: number, d: number) => new BoxGeometry(w, h, d).translate(0, h / 2, 0);

function triangle(points: [number, number][], depth: number): BufferGeometry {
  const s = new Shape();
  points.forEach(([x, y], i) => (i === 0 ? s.moveTo(x, y) : s.lineTo(x, y)));
  s.closePath();
  return new ExtrudeGeometry(s, { depth, bevelEnabled: false }).translate(0, 0, -depth / 2);
}

/** Round wooden plinth with an owner-colour ring, shared by all four pieces. */
function plinth(): { body: BufferGeometry[]; cloth: BufferGeometry[] } {
  return {
    body: [part(new CylinderGeometry(0.24, 0.27, 0.08, 12).translate(0, 0.04, 0), WOOD)],
    cloth: [part(new CylinderGeometry(0.265, 0.265, 0.035, 12).translate(0, 0.085, 0), CLOTH)],
  };
}

function sloop(): PieceModel {
  const base = plinth();
  const hull = triangle(
    [[-0.22, 0.22], [0.2, 0.22], [0.12, 0.05], [-0.14, 0.05]],
    0.2,
  );
  return {
    body: merge([
      ...base.body,
      part(hull, WOOD, { at: [0, 0.1, 0] }),
      part(new ConeGeometry(0.1, 0.2, 4).rotateZ(-Math.PI / 2), WOOD, { at: [0.28, 0.27, 0] }),
      part(cyl(0.015, 0.62, 5), WOOD, { at: [0, 0.3, 0] }),
      part(new SphereGeometry(0.03, 6, 5), BRASS, { at: [0, 0.94, 0] }),
      part(box(0.28, 0.015, 0.015), WOOD, { at: [0.0, 0.78, 0] }),
    ]),
    cloth: merge([
      ...base.cloth,
      part(triangle([[0.02, 0.38], [0.02, 0.85], [0.26, 0.4]], 0.015), CLOTH, { at: [0.0, 0.0, 0.02] }),
      part(triangle([[-0.02, 0.4], [-0.02, 0.8], [-0.2, 0.4]], 0.015), CLOTH, { at: [0.0, 0.0, 0.02] }),
    ]),
  };
}

function skull(): PieceModel {
  const base = plinth();
  return {
    body: merge([
      ...base.body,
      part(cyl(0.02, 0.9, 5), WOOD, { at: [-0.1, 0.1, 0] }),
      part(new SphereGeometry(0.045, 7, 5), BRASS, { at: [-0.1, 1.02, 0] }),
      part(new SphereGeometry(0.07, 8, 6), BONE, { at: [0.12, 0.8, 0.03] }),
      part(box(0.07, 0.04, 0.05), BONE, { at: [0.12, 0.7, 0.03] }),
      part(box(0.02, 0.03, 0.02), IRON, { at: [0.095, 0.82, 0.09] }),
      part(box(0.02, 0.03, 0.02), IRON, { at: [0.145, 0.82, 0.09] }),
      part(box(0.3, 0.02, 0.02), BONE, { at: [0.12, 0.62, 0.03], rot: [0, 0, 0.5] }),
      part(box(0.3, 0.02, 0.02), BONE, { at: [0.12, 0.62, 0.03], rot: [0, 0, -0.5] }),
    ]),
    cloth: merge([...base.cloth, part(box(0.5, 0.36, 0.02), CLOTH, { at: [0.15, 0.62, 0] })]),
  };
}

function compass(): PieceModel {
  const base = plinth();
  const face = new CylinderGeometry(0.2, 0.2, 0.03, 14).rotateX(Math.PI / 2);
  const ring = new TorusGeometry(0.2, 0.025, 6, 16);
  return {
    body: merge([
      ...base.body,
      part(cyl(0.03, 0.22, 6), WOOD, { at: [0, 0.1, 0] }),
      part(box(0.3, 0.05, 0.12), WOOD, { at: [0, 0.08, 0] }),
      part(ring, BRASS, { at: [0, 0.55, 0] }),
      part(new CylinderGeometry(0.02, 0.03, 0.06, 6).rotateX(Math.PI / 2), BRASS, { at: [0, 0.55, 0.03] }),
      part(new ConeGeometry(0.035, 0.34, 4).rotateZ(0), IRON, { at: [0, 0.55, 0.045], rot: [0, 0, 0.6] }),
      part(new SphereGeometry(0.03, 6, 5), BRASS, { at: [0, 0.8, 0] }),
    ]),
    cloth: merge([...base.cloth, part(face, CLOTH, { at: [0, 0.55, 0] })]),
  };
}

function anchor(): PieceModel {
  const base = plinth();
  return {
    body: merge([
      ...base.body,
      part(cyl(0.035, 0.75, 6), IRON, { at: [0, 0.1, 0] }),
      part(box(0.34, 0.05, 0.05), IRON, { at: [0, 0.72, 0] }),
      part(new TorusGeometry(0.04, 0.012, 5, 10), BRASS, { at: [0, 0.92, 0] }),
      part(new TorusGeometry(0.2, 0.035, 6, 12, Math.PI), IRON, { at: [0, 0.3, 0], rot: [0, 0, Math.PI] }),
      part(new ConeGeometry(0.06, 0.12, 4), IRON, { at: [0.2, 0.37, 0], rot: [0, 0, -0.4] }),
      part(new ConeGeometry(0.06, 0.12, 4), IRON, { at: [-0.2, 0.37, 0], rot: [0, 0, 0.4] }),
    ]),
    cloth: merge([...base.cloth, part(cyl(0.05, 0.16, 8), CLOTH, { at: [0, 0.44, 0] })]),
  };
}

const builders: Record<EmblemName, () => PieceModel> = { sun: sloop, wave: skull, star: compass, anchor };

/** The carved-and-brass model for the seat with this emblem. Caller disposes both geometries. */
export function pieceModel(emblem: EmblemName): PieceModel {
  return builders[emblem]();
}
