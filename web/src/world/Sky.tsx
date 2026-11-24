import { useEffect, useMemo } from "react";
import { BackSide, BufferAttribute, Color, ConeGeometry, DodecahedronGeometry, SphereGeometry, type BufferGeometry, type Texture } from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { sunKeyframes, worldColors, type Mood } from "../styles/tokens";
import { paint } from "./palette";

const DOME_RADIUS = 150;
/** Pale haze at the horizon, so the sea meets the sky in a soft band instead of a seam. Night uses moonlight. */
const HAZE: Record<Mood, string> = { day: worldColors.sand, night: sunKeyframes.night };

/** Distant islets on the horizon, fixed in place, as one merged mesh that the fog softens. */
function isletGeometry(): BufferGeometry {
  const spots: [number, number, number][] = [
    [-0.4, 70, 1.6], [0.35, 85, 2.4], [1.3, 64, 1.2], [2.2, 92, 2.8], [3.0, 75, 1.8], [3.9, 88, 2.2], [4.8, 68, 1.4], [5.6, 80, 2.0],
  ];
  const parts = spots.flatMap(([a, r, s]) => {
    const x = Math.cos(a) * r;
    const z = Math.sin(a) * r;
    return [
      paint(new DodecahedronGeometry(s, 0).scale(1.8, 0.45, 1.1).translate(x, -0.1, z), "world.sand").toNonIndexed(),
      paint(new ConeGeometry(s * 0.7, s * 1.4, 5).translate(x + s * 0.3, s * 0.55, z), "district.kelp").toNonIndexed(),
    ];
  });
  const merged = mergeGeometries(parts.map((g) => (g.index ? g.toNonIndexed() : g)));
  if (!merged) throw new Error("Islet parts do not share attributes");
  return merged;
}

/** A sky dome whose vertex colours run from haze at the horizon to `sky` overhead. */
function domeGeometry(sky: Color, haze: Color): BufferGeometry {
  const g = new SphereGeometry(DOME_RADIUS, 24, 12);
  const pos = g.attributes.position;
  const colors = new Float32Array(pos.count * 3);
  const c = new Color();
  // Half haze, half sky at the horizon, so night keeps a dark horizon instead of a sand band.
  const horizon = sky.clone().lerp(haze, 0.5);
  for (let i = 0; i < pos.count; i += 1) {
    const up = Math.max(0, pos.getY(i) / DOME_RADIUS);
    c.copy(horizon).lerp(sky, Math.min(1, Math.pow(up, 0.6) * 1.2));
    c.toArray(colors, i * 3);
  }
  g.setAttribute("color", new BufferAttribute(colors, 3));
  return g;
}

/**
 * Sky dome and horizon. The dome blends from haze at the horizon to the mood's sky colour
 * overhead, through vertex colours, and ignores fog so it stays the backdrop.
 */
export function Sky({ sky, mood, texture }: { sky: Color; mood: Mood; texture: Texture }) {
  const hex = sky.getHex();
  const dome = useMemo(() => domeGeometry(new Color(hex), new Color(HAZE[mood])), [hex, mood]);
  useEffect(() => () => dome.dispose(), [dome]);
  const islets = useMemo(() => isletGeometry(), []);
  return (
    <group>
      <mesh geometry={dome}>
        <meshBasicMaterial vertexColors side={BackSide} fog={false} depthWrite={false} />
      </mesh>
      <mesh geometry={islets}>
        <meshLambertMaterial map={texture} />
      </mesh>
    </group>
  );
}
