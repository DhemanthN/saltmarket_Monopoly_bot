import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import { type PerspectiveCamera, Vector3 } from "three";
import { activeShake, headingFromDirection, isCalm, isDecisionOpen, isIntroGateOpen, releaseIntro, setHeading, shakeDecay } from "./cameraBus";
import { INTRO_SECONDS, INTRO_START_SCALE, PARALLAX_AMOUNT, SHAKE_FOV_PUNCH, introProgress, pointerUnit, shakeOffset, swayOffset } from "./cameraMotion";
import { piecePositions } from "./piecePositions";
import { CHART_DIR, CHART_TARGET, chartDistance } from "./chartFit";
import { roadForward } from "./layout";

export type CameraView = "street" | "chart";

/** Damping rate so a camera toggle settles in about one `travel` (480 ms). */
const DAMP = 9;
const STREET_BACK = 4.0;
const STREET_UP = 2.4;
/** Kept short so the followed piece sits in the lower third of the frame, not below it. */
const STREET_AHEAD = 1.8;
/** Look-at height: high enough that the road fills the lower third, not the lower half. */
const STREET_LOOK_Y = 0.7;
/** Portrait screens look higher, so the road does not fill the lower half of a tall frame. */
const PORTRAIT_LOOK_Y = 1.3;
/** Portrait screens back off further so the lots beside the road stay in frame. */
const PORTRAIT_BACK = 2.4;
/**
 * Share of a bottom HUD inset the picture moves up by. Half would centre the old centre in the
 * open area; the followed piece sits below centre, so it needs more to clear the sheet.
 */
const INSET_SHIFT = 0.75;
/** Chart view centres the ring in the open area, which is half the inset. */
const CHART_INSET_SHIFT = 0.5;
/** The intro waits this long for the loading screen to let go before it starts anyway. */
const INTRO_GATE_TIMEOUT_S = 6;
/** How quickly parallax follows the pointer. */
const PARALLAX_DAMP = 3;
const FINE_POINTER = "(pointer: fine)";

interface Props {
  view: CameraView;
  /** Seat the street camera follows: the human, or seat 0 in a watched game. */
  followSeat: number;
  /** Space that seat stands on, so the camera faces along the road. */
  followSpace: number;
  reducedMotion: boolean;
  /** Screen pixels hidden by the HUD at the bottom. The view shifts up by `INSET_SHIFT` of it. */
  bottomInset: number;
}

type IntroState = "waiting" | "playing" | "done";

/**
 * Street view sits behind and above the followed piece, looking down the road. Chart view looks
 * down on the whole atoll. Both damp toward their pose; reduced motion cuts instead.
 *
 * Extra motion, all off in Calm and under reduced motion: a 2.5 s intro swoop from above the
 * chart pose (a click or key ends it), a tiny idle sway, mouse parallax (fine pointers only, held
 * still while a decision is open) and the cannon shake with a field-of-view punch. The compass
 * heading is published from the real camera direction.
 */
export function CameraRig({ view, followSeat, followSpace, reducedMotion, bottomInset }: Props) {
  const { camera, invalidate, size } = useThree();
  const target = useRef(new Vector3().copy(CHART_TARGET));
  const goalPos = useMemo(() => new Vector3(), []);
  const goalTarget = useMemo(() => new Vector3(), []);
  const forward = useMemo(() => new Vector3(), []);
  const base = useMemo(() => new Vector3(), []);
  const direction = useMemo(() => new Vector3(), []);
  const right = useMemo(() => new Vector3(), []);
  const up = useMemo(() => new Vector3(), []);
  const introStart = useMemo(() => new Vector3(), []);
  const first = useRef(true);
  const intro = useRef<{ state: IntroState; elapsed: number; waited: number }>({ state: "done", elapsed: 0, waited: 0 });
  const pointer = useRef({ x: 0, y: 0, smoothX: 0, smoothY: 0 });
  const clock = useRef(0);
  const fov = (camera as PerspectiveCamera).fov;
  const baseFov = useRef(fov);
  const chartAt = useMemo(() => chartDistance(size.width, size.height, bottomInset, fov), [size.width, size.height, bottomInset, fov]);

  useEffect(() => invalidate(), [view, followSpace, followSeat, size, chartAt, invalidate]);

  // Centre the picture in the part of the screen the HUD leaves open, so a bottom sheet
  // never hides the followed piece. The frustum moves; the camera pose does not.
  useEffect(() => {
    const perspective = camera as PerspectiveCamera;
    if (bottomInset > 0) {
      // Chart view centres the whole ring in the open area; street view lifts the piece clear of it.
      const shift = view === "chart" ? CHART_INSET_SHIFT : INSET_SHIFT;
      perspective.setViewOffset(size.width, size.height, 0, bottomInset * shift, size.width, size.height);
    } else {
      perspective.clearViewOffset();
    }
    invalidate();
  }, [camera, bottomInset, size, view, invalidate]);

  // A click, tap or key ends the intro where it is; the damping then carries the camera in.
  useEffect(() => {
    const skip = () => {
      if (intro.current.state === "done") return;
      intro.current.state = "done";
      releaseIntro();
      invalidate();
    };
    window.addEventListener("pointerdown", skip);
    window.addEventListener("keydown", skip);
    return () => {
      window.removeEventListener("pointerdown", skip);
      window.removeEventListener("keydown", skip);
    };
  }, [invalidate]);

  // Parallax follows a mouse, not a finger.
  useEffect(() => {
    if (!window.matchMedia?.(FINE_POINTER).matches) return;
    const move = (e: PointerEvent) => {
      Object.assign(pointer.current, pointerUnit(e.clientX, e.clientY, window.innerWidth, window.innerHeight));
      invalidate();
    };
    window.addEventListener("pointermove", move);
    return () => window.removeEventListener("pointermove", move);
  }, [invalidate]);

  useEffect(() => {
    const perspective = camera as PerspectiveCamera;
    const original = baseFov.current;
    return () => {
      perspective.fov = original;
      perspective.updateProjectionMatrix();
    };
  }, [camera]);

  useFrame((state, dt) => {
    const calm = reducedMotion || isCalm();
    clock.current += dt;
    if (view === "chart") {
      goalPos.copy(CHART_TARGET).addScaledVector(CHART_DIR, chartAt);
      goalTarget.copy(CHART_TARGET);
    } else {
      const p = piecePositions[followSeat];
      roadForward(followSpace, forward);
      const portrait = size.width < size.height;
      const back = STREET_BACK + (portrait ? PORTRAIT_BACK : 0);
      goalPos.copy(p).addScaledVector(forward, -back).setY(p.y + STREET_UP + (portrait ? 0.8 : 0));
      // Pull slightly toward the lagoon so the lots on the outside stay in frame.
      goalPos.multiplyScalar(0.92);
      goalTarget.copy(p).addScaledVector(forward, STREET_AHEAD).setY(portrait ? PORTRAIT_LOOK_Y : STREET_LOOK_Y);
    }

    if (first.current) {
      first.current = false;
      base.copy(goalPos);
      // The swoop opens high above the chart pose and glides down to the street pose.
      if (!calm && view === "street") {
        introStart.copy(CHART_TARGET).addScaledVector(CHART_DIR, chartAt * INTRO_START_SCALE);
        intro.current = { state: "waiting", elapsed: 0, waited: 0 };
      }
    }

    const swoop = intro.current;
    if (swoop.state === "waiting") {
      swoop.waited += dt;
      if (isIntroGateOpen() || swoop.waited > INTRO_GATE_TIMEOUT_S) {
        releaseIntro();
        swoop.state = "playing";
      }
    }
    if (swoop.state === "playing") {
      swoop.elapsed += dt;
      if (swoop.elapsed >= INTRO_SECONDS) swoop.state = "done";
    }

    if (swoop.state === "done") {
      const k = reducedMotion ? 1 : 1 - Math.exp(-DAMP * dt);
      base.lerp(goalPos, k);
      target.current.lerp(goalTarget, k);
    } else {
      const p = swoop.state === "waiting" ? 0 : introProgress(swoop.elapsed);
      base.lerpVectors(introStart, goalPos, p);
      target.current.lerpVectors(CHART_TARGET, goalTarget, p);
      invalidate();
    }

    let offsetX = 0;
    let offsetY = 0;
    if (!calm && view === "street" && swoop.state === "done") {
      // Sway needs a render every frame, so it runs only when the loop does.
      if (state.frameloop === "always") {
        const sway = swayOffset(clock.current);
        offsetX += sway.x;
        offsetY += sway.y;
      }
      const p = pointer.current;
      const goalX = isDecisionOpen() ? 0 : p.x;
      const goalY = isDecisionOpen() ? 0 : p.y;
      const follow = 1 - Math.exp(-PARALLAX_DAMP * dt);
      p.smoothX += (goalX - p.smoothX) * follow;
      p.smoothY += (goalY - p.smoothY) * follow;
      offsetX += p.smoothX * PARALLAX_AMOUNT;
      offsetY -= p.smoothY * PARALLAX_AMOUNT * 0.5;
      if (Math.abs(goalX - p.smoothX) + Math.abs(goalY - p.smoothY) > 1e-3) invalidate();
    }

    const now = performance.now();
    const shake = calm ? null : activeShake(now);
    const perspective = state.camera as PerspectiveCamera;
    let nextFov = baseFov.current;
    if (shake) {
      const strength = shake.intensity * shakeDecay(shake, now);
      const rattle = shakeOffset(strength, now / 1000);
      offsetX += rattle.x;
      offsetY += rattle.y;
      nextFov += SHAKE_FOV_PUNCH * strength;
      invalidate();
    }
    if (perspective.fov !== nextFov) {
      perspective.fov = nextFov;
      perspective.updateProjectionMatrix();
    }

    camera.position.copy(base);
    if (offsetX !== 0 || offsetY !== 0) {
      camera.lookAt(target.current);
      camera.getWorldDirection(direction);
      right.crossVectors(direction, camera.up).normalize();
      up.crossVectors(right, direction).normalize();
      camera.position.addScaledVector(right, offsetX).addScaledVector(up, offsetY);
    }
    camera.lookAt(target.current);

    camera.getWorldDirection(direction);
    if (Math.hypot(direction.x, direction.z) > 0.2) setHeading(headingFromDirection(direction.x, direction.z));

    if (base.distanceToSquared(goalPos) > 1e-4) invalidate();
  });

  return null;
}
