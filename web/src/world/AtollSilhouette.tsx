import { Canvas } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import { useLayoutEffect, useMemo, useRef } from "react";
import { BackSide, Color, InstancedMesh, Object3D } from "three";
import { Signboard } from "../ui/Signboard";
import { districts, palette, sunKeyframes } from "../styles/tokens";
import { DISTRICT_HEIGHT, RING_RADIUS, ringPosition, spaces } from "./board";

const LOT_SIZE = 1.25;
const OUTLINE_SCALE = 1.04;
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

function Atoll() {
  const home = ringPosition(0);
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
      <Html position={[home.x, 2.6, home.z]} center zIndexRange={[100, 100]} style={{ pointerEvents: "none" }}>
        <Signboard name={spaces[0].name} />
      </Html>
    </>
  );
}

/**
 * Placeholder world behind the start screen: the 40-lot ring at golden hour.
 * One static frame (`frameloop="demand"`), no idle motion. Task 4a replaces this.
 */
export function AtollSilhouette() {
  return (
    <Canvas
      frameloop="demand"
      dpr={[1, 2]}
      camera={{ position: [0, 9, 26], fov: 38, near: 0.5, far: 120 }}
      onCreated={({ camera }) => camera.lookAt(0, 0.5, 0)}
      style={{ position: "absolute", inset: 0, zIndex: "var(--z-canvas)" }}
      aria-hidden
    >
      <color attach="background" args={[SKY]} />
      <fogExp2 attach="fog" args={[SKY, 0.022]} />
      <hemisphereLight args={["#FFE6C4", palette.tide, 0.9]} />
      <directionalLight position={[-14, 6, 10]} color={sunKeyframes.dusk} intensity={2.2} />
      <Atoll />
    </Canvas>
  );
}
