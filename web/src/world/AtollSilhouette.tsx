import { Canvas, useThree } from "@react-three/fiber";
import { useLayoutEffect, useMemo, useRef, useState } from "react";
import { BackSide, Color, InstancedMesh, Object3D, Vector3 } from "three";
import { Signboard } from "../ui/Signboard";
import { districts, palette, sunKeyframes } from "../styles/tokens";
import styles from "./AtollSilhouette.module.css";
import { DISTRICT_HEIGHT, RING_RADIUS, ringPosition, spaces } from "./board";

const LOT_SIZE = 1.25;
const OUTLINE_SCALE = 1.04;
const ANCHOR_HEIGHT = 1.6;
const SKY = "#EBC9A0";

/** Lots as two instanced meshes (body and ink hull outline), so the whole ring costs two draw calls. */
function Lots() {
  const body = useRef<InstancedMesh>(null);
  const hull = useRef<InstancedMesh>(null);
  const dummy = useMemo(() => new Object3D(), []);

  useLayoutEffect(() => {
    if (!body.current || !hull.current) return;
    const color = new Color();
    spaces.forEach((space, i) => {
      const { x, z, angle } = ringPosition(i);
      const height = space.district ? DISTRICT_HEIGHT[space.district] : 0.25;
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
  }, [dummy]);

  return (
    <>
      <instancedMesh ref={body} args={[undefined, undefined, spaces.length]}>
        <boxGeometry />
        <meshLambertMaterial />
      </instancedMesh>
      <instancedMesh ref={hull} args={[undefined, undefined, spaces.length]}>
        <boxGeometry />
        <meshBasicMaterial color={palette.ink} side={BackSide} />
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
    camera.position.set(0, wide ? 15 : 40, wide ? 31 : 70);
    camera.lookAt(wide ? -4.5 : 0, wide ? -1 : -9, 0);
    camera.updateMatrixWorld();
    camera.updateProjectionMatrix();
    const home = ringPosition(0);
    const p = new Vector3(home.x, ANCHOR_HEIGHT, home.z).project(camera);
    onAnchor({ x: ((p.x + 1) / 2) * size.width, y: ((1 - p.y) / 2) * size.height });
    invalidate();
  }, [camera, size, invalidate, onAnchor]);
  return null;
}

function Atoll() {
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
      <Lots />
    </>
  );
}

/**
 * Placeholder world behind the start screen: the 40-lot ring at golden hour.
 * One static frame (`frameloop="demand"`), no idle motion. Task 4a replaces this.
 */
export function AtollSilhouette() {
  const [anchor, setAnchor] = useState<ScreenPoint | null>(null);
  return (
    <div className={styles.world} aria-hidden>
      <Canvas frameloop="demand" dpr={[1, 2]} camera={{ fov: 38, near: 0.5, far: 160 }}>
        <color attach="background" args={[SKY]} />
        <fogExp2 attach="fog" args={[SKY, 0.011]} />
        <hemisphereLight args={["#FFF0D8", "#B9A98A", 2.2]} />
        <directionalLight position={[-14, 6, 10]} color={sunKeyframes.dusk} intensity={2.6} />
        <CameraRig onAnchor={setAnchor} />
        <Atoll />
      </Canvas>
      {anchor ? (
        <div className={styles.label} style={{ left: anchor.x, top: anchor.y }}>
          <Signboard name={spaces[0].name} />
        </div>
      ) : null}
    </div>
  );
}
