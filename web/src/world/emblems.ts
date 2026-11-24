import { ExtrudeGeometry, Shape, type BufferGeometry } from "three";
import type { EmblemName } from "../styles/tokens";
import { paint } from "./palette";

/*
 * The four seat emblems as small extruded shapes for the flag on each piece, so a piece is
 * never identified by colour alone. Shapes match the custom SVG emblems in `ui/Emblem.tsx`
 * in spirit (sun, wave, star, anchor); unit size about 1 before scaling.
 */

function radial(points: number, outer: number, inner: number, turn = 0): Shape {
  const s = new Shape();
  for (let i = 0; i < points * 2; i += 1) {
    const r = i % 2 === 0 ? outer : inner;
    const a = turn + (i / (points * 2)) * Math.PI * 2;
    if (i === 0) s.moveTo(Math.cos(a) * r, Math.sin(a) * r);
    else s.lineTo(Math.cos(a) * r, Math.sin(a) * r);
  }
  s.closePath();
  return s;
}

function wave(): Shape {
  const s = new Shape();
  const steps = 16;
  for (let i = 0; i <= steps; i += 1) {
    const x = -0.5 + i / steps;
    const y = Math.sin(x * Math.PI * 3) * 0.14 + 0.1;
    if (i === 0) s.moveTo(x, y);
    else s.lineTo(x, y);
  }
  for (let i = steps; i >= 0; i -= 1) {
    const x = -0.5 + i / steps;
    s.lineTo(x, Math.sin(x * Math.PI * 3) * 0.14 - 0.12);
  }
  s.closePath();
  return s;
}

function anchor(): Shape {
  const s = new Shape();
  const pts: [number, number][] = [
    [-0.06, 0.45], [0.06, 0.45], [0.06, 0.25], [0.22, 0.25], [0.22, 0.15], [0.06, 0.15], [0.06, -0.28],
    [0.3, -0.12], [0.36, -0.2], [0, -0.45], [-0.36, -0.2], [-0.3, -0.12], [-0.06, -0.28], [-0.06, 0.15],
    [-0.22, 0.15], [-0.22, 0.25], [-0.06, 0.25],
  ];
  pts.forEach(([x, y], i) => (i === 0 ? s.moveTo(x, y) : s.lineTo(x, y)));
  s.closePath();
  return s;
}

const shapes: Record<EmblemName, () => Shape> = {
  sun: () => radial(10, 0.5, 0.32),
  wave,
  star: () => radial(5, 0.5, 0.2, Math.PI / 2),
  anchor,
};

/** Ink emblem geometry, painted into the ink cell. */
export function emblemGeometry(name: EmblemName): BufferGeometry {
  const g = new ExtrudeGeometry(shapes[name](), { depth: 0.08, bevelEnabled: false });
  g.translate(0, 0, -0.04);
  return paint(g, "ink");
}
