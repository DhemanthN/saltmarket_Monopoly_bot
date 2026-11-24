/* Three.js objects are mutable by design: the frame loop moves meshes and buffers in place. */
/* eslint-disable react-hooks/immutability */
import { useFrame } from "@react-three/fiber";
import { useEffect, useLayoutEffect, useMemo, useRef } from "react";
import {
  BufferAttribute,
  BufferGeometry,
  InstancedMesh,
  Line,
  LineBasicMaterial,
  Mesh,
  MeshBasicMaterial,
  Object3D,
  RingGeometry,
  SphereGeometry,
  Vector3,
  type Texture,
} from "three";
import { anyModalOpen, isCalm, isDecisionOpen, triggerCameraShake } from "./cameraBus";
import { useDispose } from "./dispose";
import {
  FLARE_FLIGHT_S,
  flareArc,
  flaresAllowed,
  galleonCount,
  nextFlareDelay,
  onFlareTrigger,
  patrolCurve,
  seededRandom,
} from "./effects";
import { merge, part } from "./geometry";
import { galleonGeometry } from "./landmarkKit";
import { LAGOON_RADIUS } from "./layout";
import { RING_RADIUS } from "./board";
import type { Tier } from "./quality";
import { foamMaterial, swayMaterial, worldTime } from "./shaders";

/** Motion is allowed: not Calm, not reduced motion, and not the Low tier (which renders on demand). */
function motionOn(tier: Tier, reducedMotion: boolean): boolean {
  return tier !== "low" && !reducedMotion && !isCalm();
}

/** Advances the shared shader clock while motion is on. Frozen, every flag, sail and wave holds still. */
export function WorldClock({ tier, reducedMotion }: { tier: Tier; reducedMotion: boolean }) {
  useFrame((_, dt) => {
    if (motionOn(tier, reducedMotion)) worldTime.value += Math.min(dt, 0.1);
  });
  return null;
}

/** Foam rolling onto the sand at the outer shore and the lagoon shore. One draw call. */
export function ShoreFoam() {
  const outer = RING_RADIUS + 3.4;
  const geometry = useMemo(() => {
    const ring = (a: number, b: number) => new RingGeometry(a, b, 96, 1).rotateX(-Math.PI / 2).translate(0, -0.06, 0);
    return merge([part(ring(outer, outer + 0.9), "world.white"), part(ring(LAGOON_RADIUS - 0.7, LAGOON_RADIUS), "world.white")]);
  }, [outer]);
  const material = useMemo(() => foamMaterial([LAGOON_RADIUS, outer], 0.7, "#FBF7EE"), [outer]);
  useDispose(geometry, material);
  return <mesh geometry={geometry} material={material} renderOrder={1} />;
}

/** Where each galleon is this frame, for the flare launcher. */
const galleonSpots: Vector3[] = [];

/**
 * Two or three patrol galleons on closed loops outside the reef, rocking on the swell.
 * One instanced draw call. Low tier sails none; frozen motion leaves them moored.
 */
export function Galleons({ texture, tier, reducedMotion }: { texture: Texture; tier: Tier; reducedMotion: boolean }) {
  const count = galleonCount(tier);
  const geometry = useMemo(() => galleonGeometry(), []);
  const material = useMemo(() => swayMaterial(texture, 0.12, 1.4), [texture]);
  const curves = useMemo(() => [0, 1, 2].map((i) => patrolCurve(i)), []);
  useDispose(geometry, material);
  const mesh = useRef<InstancedMesh>(null);
  const progress = useRef([0.0, 0.37, 0.71]);
  const tmp = useMemo(() => ({ o: new Object3D(), p: new Vector3(), t: new Vector3() }), []);

  const place = () => {
    const m = mesh.current;
    if (!m) return;
    galleonSpots.length = 0;
    for (let i = 0; i < count; i += 1) {
      const u = progress.current[i];
      curves[i].getPointAt(u, tmp.p);
      curves[i].getTangentAt(u, tmp.t);
      tmp.o.position.copy(tmp.p);
      tmp.o.position.y = Math.sin(worldTime.value * 1.1 + i) * 0.05;
      tmp.o.rotation.set(Math.sin(worldTime.value * 0.9 + i * 2) * 0.03, Math.atan2(tmp.t.x, tmp.t.z), Math.sin(worldTime.value * 1.3 + i) * 0.06);
      tmp.o.scale.setScalar(1.3);
      tmp.o.updateMatrix();
      m.setMatrixAt(i, tmp.o.matrix);
      galleonSpots.push(tmp.p.clone());
    }
    m.instanceMatrix.needsUpdate = true;
  };

  useLayoutEffect(place);
  useFrame((_, dt) => {
    if (count === 0 || !motionOn(tier, reducedMotion)) return;
    for (let i = 0; i < count; i += 1) progress.current[i] = (progress.current[i] + (Math.min(dt, 0.1) * 0.6) / curves[i].getLength()) % 1;
    place();
  });

  if (count === 0) return null;
  return <instancedMesh key={count} ref={mesh} args={[geometry, material, count]} frustumCulled={false} castShadow={false} />;
}

const TRAIL = 28;
const FLARE_HEIGHT = 6;
/** Flares splash on the reef just outside the sand, never on the board itself. */
const SPLASH_RADIUS = RING_RADIUS + 5.2;

/**
 * A flare every 15 to 20 seconds (or on `triggerFlare`) from a patrol galleon to the reef, on a
 * parabolic arc with a fading ribbon. It shakes the camera at launch and at the splash. It never
 * flies while a human decision or any modal is open, and is off on Low, in Calm and with
 * reduced motion. The glowing ball sits above 1.0 so the High tier's bloom catches it.
 */
export function Flare({ tier, reducedMotion }: { tier: Tier; reducedMotion: boolean }) {
  const random = useMemo(() => seededRandom(20261124), []);
  const timer = useRef({ wait: nextFlareDelay(random), t: -1, from: new Vector3(), to: new Vector3() });
  const ball = useRef<Mesh>(null);
  const splash = useRef<Mesh>(null);
  const pending = useRef(false);
  const parts = useMemo(() => {
    const geo = new BufferGeometry();
    geo.setAttribute("position", new BufferAttribute(new Float32Array(TRAIL * 3), 3));
    const colors = new Float32Array(TRAIL * 4);
    for (let i = 0; i < TRAIL; i += 1) colors.set([1.6, 1.1, 0.6, (1 - i / TRAIL) ** 1.6], i * 4);
    geo.setAttribute("color", new BufferAttribute(colors, 4));
    const line = new Line(geo, new LineBasicMaterial({ vertexColors: true, transparent: true, depthWrite: false, toneMapped: false }));
    line.frustumCulled = false;
    line.visible = false;
    return { line, ballGeo: new SphereGeometry(0.16, 8, 6), splashGeo: new RingGeometry(0.2, 0.45, 20).rotateX(-Math.PI / 2) };
  }, []);
  useDispose(parts.line.geometry, parts.line.material as LineBasicMaterial, parts.ballGeo, parts.splashGeo);
  const scratch = useMemo(() => new Vector3(), []);

  useEffect(() => onFlareTrigger(() => (pending.current = true)), []);

  const hide = () => {
    timer.current.t = -1;
    parts.line.visible = false;
    if (ball.current) ball.current.visible = false;
    if (splash.current) splash.current.visible = false;
  };

  useFrame((_, rawDt) => {
    const dt = Math.min(rawDt, 0.1);
    const allowed = flaresAllowed({ tier, reducedMotion, calm: isCalm(), decisionOpen: isDecisionOpen() || anyModalOpen() });
    const s = timer.current;
    if (!allowed) {
      pending.current = false;
      if (s.t >= 0) hide();
      return;
    }
    if (s.t < 0) {
      s.wait -= dt;
      if ((s.wait > 0 && !pending.current) || galleonSpots.length === 0) return;
      pending.current = false;
      s.wait = nextFlareDelay(random);
      s.from.copy(galleonSpots[Math.floor(random() * galleonSpots.length)]).setY(1.4);
      const a = Math.atan2(s.from.z, s.from.x) + (random() - 0.5) * 0.6;
      s.to.set(Math.cos(a) * SPLASH_RADIUS, -0.05, Math.sin(a) * SPLASH_RADIUS);
      s.t = 0;
      triggerCameraShake(0.25, 0.35);
    }
    const before = s.t;
    s.t += dt / FLARE_FLIGHT_S;
    const pos = parts.line.geometry.getAttribute("position") as BufferAttribute;
    for (let i = 0; i < TRAIL; i += 1) {
      flareArc(s.from, s.to, FLARE_HEIGHT, s.t - i * 0.012, scratch);
      pos.setXYZ(i, scratch.x, scratch.y, scratch.z);
    }
    pos.needsUpdate = true;
    const flying = s.t < 1;
    parts.line.visible = s.t < 1.3;
    if (ball.current) {
      ball.current.visible = flying;
      flareArc(s.from, s.to, FLARE_HEIGHT, s.t, ball.current.position);
    }
    if (before < 1 && s.t >= 1) triggerCameraShake(0.5, 0.6);
    if (splash.current) {
      const k = (s.t - 1) / 0.3;
      splash.current.visible = k >= 0 && k < 1;
      splash.current.position.copy(s.to);
      splash.current.scale.setScalar(1 + k * 3);
      (splash.current.material as MeshBasicMaterial).opacity = 1 - Math.max(0, k);
    }
    if (s.t >= 1.3) hide();
  });

  return (
    <group>
      <primitive object={parts.line} />
      <mesh ref={ball} geometry={parts.ballGeo} visible={false}>
        <meshBasicMaterial color={[4, 2.6, 1.2]} toneMapped={false} />
      </mesh>
      <mesh ref={splash} geometry={parts.splashGeo} visible={false}>
        <meshBasicMaterial color="#FBF7EE" transparent depthWrite={false} />
      </mesh>
    </group>
  );
}
