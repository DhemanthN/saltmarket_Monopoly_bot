import { Canvas, useThree } from "@react-three/fiber";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { BackSide, Color, InstancedMesh, Object3D, Vector3 } from "three";
import { Signboard } from "../ui/Signboard";
import { districts, palette, sunKeyframes } from "../styles/tokens";
import styles from "./AtollSilhouette.module.css";
import { DISTRICT_HEIGHT, RING_RADIUS, ringPosition, spaces } from "./board";

const LOT_SIZE = 1.25;
const OUTLINE_SCALE = 1.04;
const ANCHOR_HEIGHT = 1.6;
const SKY = "#EBC9A0";

/** How far lot `index` has risen when `built` (0 to 1) of the ring is done. Lots rise in board order. */
function riseOf(index: number, built: number): number {
  const t = Math.min(1, Math.max(0, built * spaces.length - index));
  return t * t * (3 - 2 * t);
}

/** Lots as two instanced meshes (body and ink hull outline), so the whole ring costs two draw calls. */
function Lots({ built }: { built: number }) {
  const { invalidate } = useThree();
  const body = useRef<InstancedMesh>(null);
  const hull = useRef<InstancedMesh>(null);
  const dummy = useMemo(() => new Object3D(), []);

  useLayoutEffect(() => {
    if (!body.current || !hull.current) return;
    const color = new Color();
    spaces.forEach((space, i) => {
      const { x, z, angle } = ringPosition(i);
      const rise = riseOf(i, built);
      const height = Math.max(0.001, (space.district ? DISTRICT_HEIGHT[space.district] : 0.25) * rise);
      dummy.position.set(x, height / 2, z);
      dummy.rotation.set(0, -angle + Math.PI / 2, 0);
      dummy.scale.set(LOT_SIZE, height, LOT_SIZE);
      dummy.updateMatrix();
      body.current!.setMatrixAt(i, dummy.matrix);
      body.current!.setColorAt(i, color.set(space.district ? districts[space.district] : palette.sailcloth));
      dummy.scale.multiplyScalar(OUTLINE_SCALE);
      dummy.updateMatrix();
      hull.current!.setMatrixAt(i, dummy.matrix);
    });
    body.current.instanceMatrix.needsUpdate = true;
    if (body.current.instanceColor) body.current.instanceColor.needsUpdate = true;
    hull.current.instanceMatrix.needsUpdate = true;
    invalidate();
  }, [dummy, built, invalidate]);

  return (
    <>
      <instancedMesh ref={body} args={[undefined, undefined, spaces.length]}>
        <boxGeometry />
        <meshLambertMaterial />
      </instancedMesh>
      <instancedMesh ref={hull} args={[undefined, undefined, spaces.length]}>
        <boxGeometry />
        <meshBasicMaterial color={palette.ink} side={BackSide} polygonOffset polygonOffsetFactor={1} polygonOffsetUnits={1} />
      </instancedMesh>
    </>
  );
}

interface ScreenPoint {
  x: number;
  y: number;
}

/**
 * Frames the ring beside the start panel. On wide screens the panel covers the left, so the
 * ring shifts right. On narrow screens the panel covers the bottom, so the ring shifts up.
 * Also reports where Home Quay's signboard anchor lands on screen.
 */
function CameraRig({ onAnchor }: { onAnchor: (p: ScreenPoint) => void }) {
  const { camera, size, invalidate } = useThree();
  useLayoutEffect(() => {
    const wide = size.width / size.height > 1;
    camera.position.set(0, wide ? 15 : 44, wide ? 31 : 78);
    camera.lookAt(wide ? -4.5 : 0, wide ? -1 : -16, 0);
    camera.updateMatrixWorld();
    camera.updateProjectionMatrix();
    const home = ringPosition(0);
    const p = new Vector3(home.x, ANCHOR_HEIGHT, home.z).project(camera);
    onAnchor({ x: ((p.x + 1) / 2) * size.width, y: ((1 - p.y) / 2) * size.height });
    invalidate();
  }, [camera, size, invalidate, onAnchor]);
  return null;
}

function Atoll({ built }: { built: number }) {
  return (
    <>
      <mesh rotation-x={-Math.PI / 2} position-y={-0.3}>
        <planeGeometry args={[240, 240]} />
        <meshLambertMaterial color={palette.tide} />
      </mesh>
      <mesh rotation-x={-Math.PI / 2} position-y={-0.05}>
        <circleGeometry args={[RING_RADIUS + 3.2, 64]} />
        <meshLambertMaterial color={palette.paperDeep} />
      </mesh>
      <mesh rotation-x={-Math.PI / 2} position-y={0.01}>
        <ringGeometry args={[RING_RADIUS - 1.2, RING_RADIUS + 1.2, 64]} />
        <meshLambertMaterial color={palette.paper} />
      </mesh>
      <mesh rotation-x={-Math.PI / 2} position-y={0.02}>
        <circleGeometry args={[RING_RADIUS - 1.6, 64]} />
        <meshLambertMaterial color="#6FA3A8" />
      </mesh>
      <Lots built={built} />
    </>
  );
}

const RISE_MS = 700;

/** Eases toward `target` over about `RISE_MS`, or jumps there when the person prefers less motion. */
function useEased(target: number): number {
  const [value, setValue] = useState(target);
  const current = useRef(target);
  useEffect(() => {
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
      current.current = target;
      setValue(target);
      return;
    }
    const from = current.current;
    const begin = performance.now();
    let frame = requestAnimationFrame(function step(now) {
      const t = Math.min(1, (now - begin) / RISE_MS);
      current.current = from + (target - from) * (1 - (1 - t) ** 3);
      setValue(current.current);
      if (t < 1) frame = requestAnimationFrame(step);
    });
    return () => cancelAnimationFrame(frame);
  }, [target]);
  return value;
}

export interface AtollSilhouetteProps {
  /** Share of the engine load done (0 to 1). The lots rise as it grows. Omit for the finished ring. */
  progress?: number;
  /** What is loading, shown on the Home Quay signboard while `progress` is below 1. */
  caption?: string;
}

/**
 * The 40-lot ring at golden hour, behind the start screen and the loading screen.
 * Renders on demand only: frames are drawn while the lots rise, then it stays still.
 */
export function AtollSilhouette({ progress = 1, caption }: AtollSilhouetteProps) {
  const [anchor, setAnchor] = useState<ScreenPoint | null>(null);
  const built = useEased(progress);
  const loading = progress < 1 && caption;
  return (
    <div className={styles.world} aria-hidden>
      <Canvas frameloop="demand" dpr={[1, 2]} camera={{ fov: 38, near: 0.5, far: 160 }}>
        <color attach="background" args={[SKY]} />
        <fogExp2 attach="fog" args={[SKY, 0.011]} />
        <hemisphereLight args={["#FFF0D8", "#B9A98A", 2.2]} />
        <directionalLight position={[-14, 6, 10]} color={sunKeyframes.dusk} intensity={2.6} />
        <CameraRig onAnchor={setAnchor} />
        <Atoll built={built} />
      </Canvas>
      {anchor ? (
        <div className={styles.label} style={{ left: anchor.x, top: anchor.y }}>
          {loading ? (
            <Signboard name={caption} price={`${Math.round(built * 100)}%`} />
          ) : (
            <Signboard name={spaces[0].name} />
          )}
        </div>
      ) : null}
    </div>
  );
}
