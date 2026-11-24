import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import { BackSide, InstancedMesh, Object3D, Vector3, type Texture } from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { BoxGeometry, CylinderGeometry } from "three";
import { motion, palette } from "../styles/tokens";
import { harbourSpot, lotTransform } from "./layout";
import { paint } from "./palette";
import type { RentTrace } from "./reduceEvents";

const POOL = 4;
/** Two `travel` legs: lot to the road's inner edge, then across the lagoon to the harbour. */
const TRIP_SECONDS = (motion.travel.ms * 2) / 1000;

interface Trip {
  from: Vector3;
  to: Vector3;
  t: number;
}

function cartGeometry() {
  const parts = [
    paint(new BoxGeometry(0.42, 0.14, 0.3).translate(0, 0.12, 0), "district.driftwood"),
    paint(new CylinderGeometry(0.11, 0.11, 0.06, 10).rotateZ(Math.PI / 2).translate(0, 0.06, 0.16), "ink"),
    paint(new CylinderGeometry(0.11, 0.11, 0.06, 10).rotateZ(Math.PI / 2).translate(0, 0.06, -0.16), "ink"),
    paint(new CylinderGeometry(0.1, 0.1, 0.16, 10).translate(0, 0.27, 0), "brass"),
  ];
  const merged = mergeGeometries(parts.map((g) => g.toNonIndexed()));
  if (!merged) throw new Error("Cart parts do not share attributes");
  return merged;
}

/** Rent sends a coin cart from the lot to the owner's harbour. Up to four at once, pooled. */
export function CoinCarts({ rent, texture, reducedMotion }: { rent: RentTrace | null; texture: Texture; reducedMotion: boolean }) {
  const geometry = useMemo(() => cartGeometry(), []);
  const body = useRef<InstancedMesh>(null);
  const hull = useRef<InstancedMesh>(null);
  const trips = useRef<(Trip | null)[]>(Array(POOL).fill(null));
  const lastSeq = useRef(rent?.seq ?? -1);
  const dummy = useMemo(() => new Object3D(), []);
  const invalidate = useThree((s) => s.invalidate);

  useEffect(() => {
    if (!rent || rent.seq === lastSeq.current) return;
    const skipped = rent.seq < lastSeq.current;
    lastSeq.current = rent.seq;
    if (skipped || reducedMotion) return;
    const slot = trips.current.findIndex((t) => t === null);
    const lot = lotTransform(rent.space);
    trips.current[slot === -1 ? 0 : slot] = { from: new Vector3(lot.x, 0, lot.z), to: harbourSpot(rent.payee), t: 0 };
    invalidate();
  }, [rent, reducedMotion, invalidate]);

  useFrame((_, dt) => {
    let active = false;
    trips.current.forEach((trip, i) => {
      if (trip) {
        trip.t += dt / TRIP_SECONDS;
        if (trip.t >= 1) trips.current[i] = null;
      }
      const live = trips.current[i];
      if (live) {
        active = true;
        const e = live.t < 0.5 ? 4 * live.t ** 3 : 1 - (-2 * live.t + 2) ** 3 / 2;
        dummy.position.lerpVectors(live.from, live.to, e);
        dummy.lookAt(live.to.x, dummy.position.y, live.to.z);
        dummy.scale.setScalar(1);
      } else {
        dummy.scale.setScalar(1e-4);
      }
      dummy.updateMatrix();
      body.current?.setMatrixAt(i, dummy.matrix);
      dummy.scale.multiplyScalar(1.06);
      dummy.updateMatrix();
      hull.current?.setMatrixAt(i, dummy.matrix);
    });
    if (body.current) body.current.instanceMatrix.needsUpdate = true;
    if (hull.current) hull.current.instanceMatrix.needsUpdate = true;
    if (active) invalidate();
  });

  return (
    <>
      <instancedMesh ref={body} args={[geometry, undefined, POOL]} frustumCulled={false}>
        <meshLambertMaterial map={texture} />
      </instancedMesh>
      <instancedMesh ref={hull} args={[geometry, undefined, POOL]} frustumCulled={false}>
        <meshBasicMaterial color={palette.ink} side={BackSide} polygonOffset polygonOffsetFactor={1} polygonOffsetUnits={1} />
      </instancedMesh>
    </>
  );
}
