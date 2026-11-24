import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import { Vector3 } from "three";
import { piecePositions } from "./piecePositions";
import { roadForward } from "./layout";

export type CameraView = "street" | "chart";

/** Damping rate so a camera toggle settles in about one `travel` (480 ms). */
const DAMP = 9;
const CHART_POSITION = new Vector3(0, 30, 21);
const CHART_TARGET = new Vector3(0, 0, 0.5);
const STREET_BACK = 4.2;
const STREET_UP = 2.6;
const STREET_AHEAD = 2.5;

interface Props {
  view: CameraView;
  /** Seat the street camera follows: the human, or seat 0 in a watched game. */
  followSeat: number;
  /** Space that seat stands on, so the camera faces along the road. */
  followSpace: number;
  reducedMotion: boolean;
}

/**
 * Street view sits behind and above the followed piece, looking down the road. Chart view looks
 * down on the whole atoll. Both damp toward their pose; reduced motion cuts instead.
 */
export function CameraRig({ view, followSeat, followSpace, reducedMotion }: Props) {
  const { camera, invalidate } = useThree();
  const target = useRef(new Vector3().copy(CHART_TARGET));
  const goalPos = useMemo(() => new Vector3(), []);
  const goalTarget = useMemo(() => new Vector3(), []);
  const forward = useMemo(() => new Vector3(), []);
  const first = useRef(true);

  useEffect(() => invalidate(), [view, followSpace, invalidate]);

  useFrame((_, dt) => {
    if (view === "chart") {
      goalPos.copy(CHART_POSITION);
      goalTarget.copy(CHART_TARGET);
    } else {
      const p = piecePositions[followSeat];
      roadForward(followSpace, forward);
      goalPos.copy(p).addScaledVector(forward, -STREET_BACK).setY(p.y + STREET_UP);
      // Pull slightly toward the lagoon so the lots on the outside stay in frame.
      goalPos.multiplyScalar(0.92);
      goalTarget.copy(p).addScaledVector(forward, STREET_AHEAD).setY(0.6);
    }
    const k = reducedMotion || first.current ? 1 : 1 - Math.exp(-DAMP * dt);
    first.current = false;
    camera.position.lerp(goalPos, k);
    target.current.lerp(goalTarget, k);
    camera.lookAt(target.current);
    if (camera.position.distanceToSquared(goalPos) > 1e-4) invalidate();
  });

  return null;
}
