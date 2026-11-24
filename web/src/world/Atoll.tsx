import { useDispose } from "./dispose";
import { useMemo } from "react";
import { CircleGeometry, CylinderGeometry, DodecahedronGeometry, RingGeometry, Shape, ShapeGeometry, type BufferGeometry, type Texture } from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { RING_RADIUS } from "./board";
import { BRIG_ROCK, HARBOUR_RADIUS, LAGOON_RADIUS, MARKET_RADIUS, ROAD_WIDTH, harbourSpot } from "./layout";
import { nonIndexed, paint } from "./palette";
import { seatOrder } from "../styles/tokens";

const flat = (g: BufferGeometry, y: number) => g.rotateX(-Math.PI / 2).translate(0, y, 0);

/**
 * Ground as one merged mesh: sand ring, road, lagoon, market square, the Brig rock, and one
 * harbour per seat in play, painted in that seat's colour (rent carts land there).
 */
function groundGeometry(seatCount: number): BufferGeometry {
  const parts: BufferGeometry[] = [
    paint(flat(new RingGeometry(LAGOON_RADIUS, RING_RADIUS + 3.4, 80, 1), 0), "world.sand"),
    paint(flat(new RingGeometry(RING_RADIUS - ROAD_WIDTH / 2, RING_RADIUS + ROAD_WIDTH / 2, 80, 1), 0.012), "world.road"),
    paint(flat(new RingGeometry(RING_RADIUS + ROAD_WIDTH / 2, RING_RADIUS + ROAD_WIDTH / 2 + 0.06, 80, 1), 0.016), "ink"),
    paint(flat(new RingGeometry(RING_RADIUS - ROAD_WIDTH / 2 - 0.06, RING_RADIUS - ROAD_WIDTH / 2, 80, 1), 0.016), "ink"),
    paint(flat(new CircleGeometry(LAGOON_RADIUS, 64), -0.08), "world.lagoon"),
    paint(new CylinderGeometry(MARKET_RADIUS, MARKET_RADIUS + 0.15, 0.22, 24).translate(0, 0.03, 0), "paper"),
    paint(new CylinderGeometry(MARKET_RADIUS * 0.45, MARKET_RADIUS * 0.45, 0.06, 16).translate(0, 0.17, 0), "brass"),
    paint(new DodecahedronGeometry(0.9, 0).scale(1.2, 0.5, 1).translate(BRIG_ROCK.x, 0.05, BRIG_ROCK.z), "world.basalt"),
  ];
  for (let seat = 0; seat < seatCount; seat += 1) {
    const h = harbourSpot(seat);
    parts.push(paint(new CylinderGeometry(0.5, 0.55, 0.12, 6).translate(h.x, 0.0, h.z), "paperDeep"));
    parts.push(paint(new CylinderGeometry(0.3, 0.3, 0.04, 6).translate(h.x, 0.08, h.z), `seat.${seatOrder[seat].name}`));
  }
  const merged = mergeGeometries(parts.map(nonIndexed));
  if (!merged) throw new Error("Ground parts do not share attributes");
  return merged;
}

/** Depth contours on the open sea, merged with the sea itself. They read as thin lines in street view. */
function seaGeometry(): BufferGeometry {
  const parts: BufferGeometry[] = [paint(flat(new CircleGeometry(160, 48), -0.15), "world.sea")];
  for (const r of [15, 19.5, 25, 32]) parts.push(paint(flat(new RingGeometry(r, r + 0.07, 96, 1), -0.11), "inkSoft"));
  return mergeAll(parts, "Sea");
}

/** Compass rose off the front-right shore: a ring and four long and four short points. Chart view only. */
function compassGeometry(): BufferGeometry {
  const [cx, cz] = [15.5, 11];
  const parts: BufferGeometry[] = [paint(flat(new RingGeometry(1.25, 1.33, 40, 1), -0.1).translate(cx, 0, cz), "inkSoft")];
  for (let i = 0; i < 8; i += 1) {
    const long = i % 2 === 0;
    const len = long ? 2.1 : 1.1;
    const w = long ? 0.22 : 0.14;
    const point = new Shape();
    point.moveTo(-w, 0);
    point.lineTo(0, len);
    point.lineTo(w, 0);
    point.closePath();
    const g = new ShapeGeometry(point).rotateZ((-i * Math.PI) / 4);
    parts.push(paint(flat(g, i === 0 ? -0.07 : -0.09 + (i % 2) * 0.01).translate(cx, 0, cz), i === 0 ? "danger" : long ? "ink" : "inkSoft"));
  }
  return mergeAll(parts, "Compass");
}

function mergeAll(parts: BufferGeometry[], what: string): BufferGeometry {
  const merged = mergeGeometries(parts.map(nonIndexed));
  if (!merged) throw new Error(`${what} parts do not share attributes`);
  return merged;
}

/** The atoll ground and the open sea. The sea has its own colour so the horizon reads as a line. */
export function Atoll({ texture, shadows, seatCount, chart }: { texture: Texture; shadows: boolean; seatCount: number; chart: boolean }) {
  const ground = useMemo(() => groundGeometry(seatCount), [seatCount]);
  const sea = useMemo(() => seaGeometry(), []);
  const compass = useMemo(() => compassGeometry(), []);
  useDispose(ground, sea, compass);
  return (
    <group>
      <mesh geometry={sea}>
        <meshLambertMaterial map={texture} />
      </mesh>
      {/* Flat on the sea it reads as a glitch from street level, so it shows only from above. */}
      <mesh geometry={compass} visible={chart}>
        <meshLambertMaterial map={texture} />
      </mesh>
      <mesh geometry={ground} receiveShadow={shadows}>
        <meshLambertMaterial map={texture} />
      </mesh>
    </group>
  );
}

export { HARBOUR_RADIUS };
