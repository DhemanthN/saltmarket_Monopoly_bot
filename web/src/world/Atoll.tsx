import { useMemo } from "react";
import { CircleGeometry, CylinderGeometry, DodecahedronGeometry, RingGeometry, type BufferGeometry, type Texture } from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { RING_RADIUS } from "./board";
import { BRIG_ROCK, HARBOUR_RADIUS, LAGOON_RADIUS, MARKET_RADIUS, ROAD_WIDTH, harbourSpot } from "./layout";
import { paint } from "./palette";

const flat = (g: BufferGeometry, y: number) => g.rotateX(-Math.PI / 2).translate(0, y, 0);

/** Ground as one merged mesh: sand ring, road, lagoon, market square, harbours and the Brig rock. */
function groundGeometry(): BufferGeometry {
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
  for (let seat = 0; seat < 4; seat += 1) {
    const h = harbourSpot(seat);
    const jetty = new CylinderGeometry(0.45, 0.5, 0.12, 6).translate(h.x, 0.0, h.z);
    parts.push(paint(jetty, "paperDeep"));
  }
  const merged = mergeGeometries(parts.map((g) => (g.index ? g.toNonIndexed() : g)));
  if (!merged) throw new Error("Ground parts do not share attributes");
  return merged;
}

/** The atoll ground and the open sea. The sea has its own colour so the horizon reads as a line. */
export function Atoll({ texture, shadows }: { texture: Texture; shadows: boolean }) {
  const ground = useMemo(() => groundGeometry(), []);
  const sea = useMemo(() => paint(flat(new CircleGeometry(160, 48), -0.15), "world.sea"), []);
  return (
    <group>
      <mesh geometry={sea}>
        <meshLambertMaterial map={texture} />
      </mesh>
      <mesh geometry={ground} receiveShadow={shadows}>
        <meshLambertMaterial map={texture} />
      </mesh>
    </group>
  );
}

export { HARBOUR_RADIUS };
