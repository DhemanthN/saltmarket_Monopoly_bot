import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import {
  AdditiveBlending,
  BufferAttribute,
  BufferGeometry,
  CanvasTexture,
  DynamicDrawUsage,
  Plane,
  PointsMaterial,
  Raycaster,
  Vector2,
  Vector3,
  type Points,
} from "three";
import { useDispose } from "./dispose";
import { EmberPool } from "./emberPool";
import { clearHover, setHover } from "./hoverStore";
import { pickSpace, spaceLabel } from "./hoverPick";
import { decorativeMotionOk, finePointer } from "./motionPref";

/** Pointer picks run at most this often; the ground-plane test is cheap but need not run per event. */
const PICK_EVERY_MS = 50;
const SPAWN_EVERY_MS = 24;
const TOUCH_LABEL_MS = 2500;
const EMBER_RGB = [1, 0.72, 0.3] as const;
const EMBER_SIZE = 14;
const FALLBACK_DISTANCE = 30;

const ground = new Plane(new Vector3(0, 1, 0), 0);

/** A soft radial dot, drawn once on a small canvas. */
function emberSprite(): CanvasTexture {
  const canvas = document.createElement("canvas");
  canvas.width = 32;
  canvas.height = 32;
  const ctx = canvas.getContext("2d")!;
  const gradient = ctx.createRadialGradient(16, 16, 0, 16, 16, 16);
  gradient.addColorStop(0, "rgba(255,255,255,1)");
  gradient.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 32, 32);
  return new CanvasTexture(canvas);
}

/**
 * Pointer effects for the world, mounted inside the Canvas. A mouse hover finds the lot under
 * the pointer (a ground-plane test, throttled) and shares its label with the spyglass cursor; a
 * touch tap shows the same label for a moment. On a mouse, with motion allowed, a golden ember
 * trail follows the pointer from a fixed pool of points.
 */
export function CursorFx() {
  const { camera, gl, invalidate } = useThree();
  const fine = useMemo(() => finePointer(), []);
  const trail = useMemo(() => fine && decorativeMotionOk(), [fine]);
  const pool = useMemo(() => new EmberPool(), []);
  const geometry = useMemo(() => {
    const g = new BufferGeometry();
    g.setAttribute("position", new BufferAttribute(pool.positions, 3).setUsage(DynamicDrawUsage));
    g.setAttribute("color", new BufferAttribute(pool.colors, 3).setUsage(DynamicDrawUsage));
    return g;
  }, [pool]);
  const material = useMemo(
    () =>
      new PointsMaterial({
        map: emberSprite(),
        size: EMBER_SIZE * Math.min(2, window.devicePixelRatio || 1),
        sizeAttenuation: false,
        vertexColors: true,
        transparent: true,
        depthTest: false,
        depthWrite: false,
        blending: AdditiveBlending,
      }),
    [],
  );
  useDispose(geometry, material, material.map);
  const points = useRef<Points>(null);

  useEffect(() => {
    const el = gl.domElement;
    const raycaster = new Raycaster();
    const ndc = new Vector2();
    const hit = new Vector3();
    let lastPick = 0;
    let lastSpawn = 0;
    let touchTimer: number | undefined;
    let label: string | null = null;

    const aim = (e: PointerEvent) => {
      const r = el.getBoundingClientRect();
      ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
      raycaster.setFromCamera(ndc, camera);
      return raycaster.ray.intersectPlane(ground, hit);
    };

    const onMove = (e: PointerEvent) => {
      if (e.pointerType !== "mouse") return;
      const now = performance.now();
      const point = aim(e);
      const distance = point ? raycaster.ray.origin.distanceTo(point) : FALLBACK_DISTANCE;
      if (trail && now - lastSpawn >= SPAWN_EVERY_MS) {
        lastSpawn = now;
        const at = raycaster.ray.at(distance, hit);
        pool.spawn(at.x, at.y, at.z);
      }
      if (now - lastPick >= PICK_EVERY_MS) {
        lastPick = now;
        const lot = point ? pickSpace(point.x, point.z) : null;
        label = lot === null ? null : spaceLabel(lot);
      }
      setHover({ label, x: e.clientX, y: e.clientY, kind: "mouse" });
      invalidate();
    };

    const onDown = (e: PointerEvent) => {
      if (e.pointerType === "mouse") return;
      const point = aim(e);
      const lot = point ? pickSpace(point.x, point.z) : null;
      window.clearTimeout(touchTimer);
      if (lot === null) {
        clearHover();
        return;
      }
      setHover({ label: spaceLabel(lot), x: e.clientX, y: e.clientY, kind: "touch" });
      touchTimer = window.setTimeout(clearHover, TOUCH_LABEL_MS);
    };

    if (fine) el.style.setProperty("cursor", "none");
    el.addEventListener("pointermove", onMove, { passive: true });
    el.addEventListener("pointerdown", onDown, { passive: true });
    el.addEventListener("pointerleave", clearHover);
    return () => {
      el.style.removeProperty("cursor");
      window.clearTimeout(touchTimer);
      el.removeEventListener("pointermove", onMove);
      el.removeEventListener("pointerdown", onDown);
      el.removeEventListener("pointerleave", clearHover);
      clearHover();
    };
  }, [camera, gl, invalidate, pool, fine, trail]);

  useFrame((_, dt) => {
    if (!trail || !points.current) return;
    const alive = pool.step(dt);
    points.current.visible = alive > 0;
    if (alive === 0) return;
    pool.tint(EMBER_RGB);
    geometry.getAttribute("position").needsUpdate = true;
    geometry.getAttribute("color").needsUpdate = true;
    invalidate();
  });

  return trail ? <points ref={points} geometry={geometry} material={material} frustumCulled={false} renderOrder={20} visible={false} /> : null;
}
