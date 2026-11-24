import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import { DoubleSide, PlaneGeometry, type Group, type PerspectiveCamera } from "three";
import { useDispose } from "../../world/dispose";
import { decorativeMotionOk } from "../../world/motionPref";
import { buildShipGeometry, SHIP_HEIGHT, SHIP_LENGTH } from "./shipGeometry";

const FOV = 30;
const SEA = "#2F7F8C";
const SEA_SEGMENTS: [number, number] = [48, 24];

/** Camera distance that frames the whole ship, with a margin, for the canvas aspect. */
function fitDistance(aspect: number): number {
  const half = Math.tan((FOV * Math.PI) / 360);
  const forWidth = (SHIP_LENGTH * 0.62) / (half * aspect);
  const forHeight = (SHIP_HEIGHT * 0.62) / half;
  return Math.max(forWidth, forHeight);
}

function Fit() {
  const { camera, size } = useThree();
  useEffect(() => {
    const cam = camera as PerspectiveCamera;
    cam.position.set(0, 2.1, fitDistance(size.width / size.height));
    cam.lookAt(0, 2.5, 0);
    cam.updateProjectionMatrix();
  }, [camera, size]);
  return null;
}

/** The ship rocks on a slow swell; the sea is one plane whose vertices ride the same swell. */
function Scene({ animate }: { animate: boolean }) {
  const ship = useMemo(() => buildShipGeometry(), []);
  const sea = useMemo(() => new PlaneGeometry(90, 60, ...SEA_SEGMENTS).rotateX(-Math.PI / 2), []);
  useDispose(ship.hull, ship.timber, ship.canvas, sea);
  const group = useRef<Group>(null);
  const { invalidate } = useThree();

  useFrame(({ clock }) => {
    const t = animate ? clock.elapsedTime : 0;
    if (group.current) {
      group.current.position.y = Math.sin(t * 0.9) * 0.08;
      group.current.rotation.z = Math.sin(t * 0.7) * 0.025;
      group.current.rotation.x = Math.sin(t * 0.5 + 1) * 0.015;
    }
    const p = sea.getAttribute("position");
    for (let i = 0; i < p.count; i += 1) {
      const x = p.getX(i);
      const z = p.getZ(i);
      p.setY(i, -0.55 + Math.sin(x * 0.7 + t * 1.1) * 0.07 + Math.sin(z * 0.9 - t * 0.8) * 0.05);
    }
    p.needsUpdate = true;
    if (!animate) return;
    invalidate();
  });

  return (
    <>
      <ambientLight intensity={1.15} />
      <directionalLight position={[-6, 9, 8]} intensity={1.9} />
      <mesh geometry={sea}>
        <meshLambertMaterial color={SEA} flatShading />
      </mesh>
      <group ref={group}>
        <mesh geometry={ship.hull}>
          <meshLambertMaterial vertexColors flatShading side={DoubleSide} />
        </mesh>
        <mesh geometry={ship.timber}>
          <meshLambertMaterial vertexColors flatShading />
        </mesh>
        <mesh geometry={ship.canvas}>
          <meshLambertMaterial vertexColors flatShading side={DoubleSide} />
        </mesh>
      </group>
    </>
  );
}

/**
 * The pirate ship sailing the lagoon, drawn broadside. It fills its own box, so the page
 * lays the box out beside the panel and the ship is never under it. Still frame when motion is off.
 */
export default function StartShip() {
  const animate = decorativeMotionOk();
  return (
    <Canvas
      frameloop={animate ? "always" : "demand"}
      dpr={[1, 1.5]}
      camera={{ fov: FOV, near: 0.5, far: 120, position: [0, 2.1, 20] }}
      gl={{ alpha: true, antialias: true, powerPreference: "low-power" }}
      aria-hidden="true"
    >
      <Fit />
      <Scene animate={animate} />
    </Canvas>
  );
}
