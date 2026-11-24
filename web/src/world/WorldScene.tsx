import { PerformanceMonitor } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { type DirectionalLight } from "three";
import { Buildings } from "./Buildings";
import { CameraRig, type CameraView } from "./CameraRig";
import { CoinCarts } from "./CoinCarts";
import { Sky } from "./Sky";
import { Signboards } from "./Signboards";
import { Atoll } from "./Atoll";
import { Pieces } from "./Pieces";
import { paletteTexture } from "./palette";
import { DEV_PERF, prefersReducedMotion, stepTier, tierSettings, type Tier } from "./quality";
import type { WorldState } from "./reduceEvents";
import { sunForTurn } from "./sun";
import styles from "./WorldScene.module.css";

// Loaded only when the high tier shows chart view, so other tiers never download it.
const ChartTiltShift = lazy(() => import("./ChartTiltShift"));

interface Props {
  state: WorldState;
  seatKinds: readonly string[];
  /** Tier the player picked; null lets the performance monitor decide. */
  tierOverride?: Tier | null;
  /** Called when the camera view changes, so a HUD can mirror it. */
  onViewChange?: (view: CameraView) => void;
}

/**
 * Sun and moon. The shadow map renders only when the board changes or the sun keyframe changes,
 * at most once per turn, never per frame.
 */
function Lights({ turn, boardVersion, shadowMapSize }: { turn: number; boardVersion: number; shadowMapSize: number | null }) {
  const sun = useMemo(() => sunForTurn(turn), [turn]);
  const light = useRef<DirectionalLight>(null);
  const { gl, scene, invalidate } = useThree();
  const shadowUpdates = useRef(0);

  // Three.js renderer and scene objects are mutable by design; R3F hands them out for this.
  /* eslint-disable react-hooks/immutability */
  useEffect(() => {
    gl.shadowMap.autoUpdate = false;
    gl.shadowMap.needsUpdate = true;
    if (shadowMapSize !== null) shadowUpdates.current += 1;
    if (DEV_PERF && window.__saltmarketPerf) window.__saltmarketPerf.shadowUpdates = shadowUpdates.current;
    invalidate();
  }, [gl, boardVersion, sun.keyframe, shadowMapSize, invalidate]);

  useEffect(() => {
    scene.background = sun.sky;
    invalidate();
  }, [scene, sun, invalidate]);
  /* eslint-enable react-hooks/immutability */

  return (
    <>
      <fogExp2 attach="fog" args={[sun.sky.getHex(), 0.014]} />
      <hemisphereLight args={["#FFF0D8", "#8C7F6A", sun.hemiIntensity]} />
      <directionalLight
        ref={light}
        position={sun.direction}
        color={sun.color}
        intensity={sun.intensity}
        castShadow={shadowMapSize !== null}
        shadow-mapSize={[shadowMapSize ?? 512, shadowMapSize ?? 512]}
        shadow-camera-left={-14}
        shadow-camera-right={14}
        shadow-camera-top={14}
        shadow-camera-bottom={-14}
        shadow-bias={-0.0005}
      />
    </>
  );
}

/** Dev-only numbers for the perf-auditor at `window.__saltmarketPerf`. */
function PerfProbe({ tier, dpr }: { tier: Tier; dpr: number }) {
  const gl = useThree((s) => s.gl);
  const frames = useRef({ n: 0, t: 0, fps: 0 });
  // The high tier's composer renders several passes per frame, and each pass would reset the
  // counters. Keep them for the whole frame and reset once here instead.
  /* eslint-disable react-hooks/immutability */
  useEffect(() => {
    gl.info.autoReset = false;
    return () => {
      gl.info.autoReset = true;
    };
  }, [gl]);
  /* eslint-enable react-hooks/immutability */
  useFrame((_, dt) => {
    const f = frames.current;
    f.n += 1;
    f.t += dt;
    if (f.t >= 0.5) {
      f.fps = Math.round(f.n / f.t);
      f.n = 0;
      f.t = 0;
    }
    window.__saltmarketPerf = {
      tier,
      dpr,
      fps: f.fps,
      drawCalls: gl.info.render.calls,
      triangles: gl.info.render.triangles,
      shadowUpdates: window.__saltmarketPerf?.shadowUpdates ?? 0,
    };
    // Runs before this frame renders, so the numbers above are the previous frame's totals.
    gl.info.reset();
  });
  return null;
}

/** The 3D atoll. It renders a `WorldState` and never reads events. */
export function WorldScene({ state, seatKinds, tierOverride = null, onViewChange }: Props) {
  const reducedMotion = useMemo(() => prefersReducedMotion(), []);
  const [autoTier, setAutoTier] = useState<Tier>(reducedMotion ? "low" : "medium");
  const tier = tierOverride ?? autoTier;
  const settings = tierSettings(tier, typeof window === "undefined" ? 1 : window.devicePixelRatio);
  const [view, setView] = useState<CameraView>("street");
  const sun = sunForTurn(state.turn);
  const texture = paletteTexture(sun.mood);
  const human = seatKinds.indexOf("human");
  // Follow the human; in a watched game follow the first seat still playing, so the camera
  // never ends on an empty street after a bankruptcy.
  const firstActive = state.bankrupt.findIndex((b) => !b);
  const followSeat = human !== -1 ? human : Math.max(0, state.winner ?? firstActive);
  const shadows = settings.shadowMapSize !== null;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() !== "c" || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.target instanceof HTMLElement && e.target.closest("input, textarea, select")) return;
      setView((v) => (v === "street" ? "chart" : "street"));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => onViewChange?.(view), [view, onViewChange]);

  return (
    <div className={styles.world}>
      <Canvas
        frameloop={settings.frameloop}
        dpr={settings.dpr}
        shadows={shadows}
        camera={{ fov: 42, near: 0.3, far: 180, position: [0, 30, 21] }}
      >
        <PerformanceMonitor
          onIncline={() => !reducedMotion && setAutoTier((t) => stepTier(t, 1))}
          onDecline={() => setAutoTier((t) => stepTier(t, -1))}
          flipflops={3}
          onFallback={() => setAutoTier("low")}
        />
        <Lights turn={state.turn} boardVersion={state.boardVersion} shadowMapSize={settings.shadowMapSize} />
        <CameraRig view={view} followSeat={followSeat} followSpace={state.position[followSeat] ?? 0} reducedMotion={reducedMotion} />
        <Sky sky={sun.sky} texture={texture} />
        <Atoll texture={texture} shadows={shadows} seatCount={seatKinds.length} />
        <Signboards state={state} fromSpace={state.position[followSeat] ?? 0} street={view === "street"} />
        <Buildings state={state} texture={texture} reducedMotion={reducedMotion} shadows={shadows} fullOutlines={settings.fullOutlines} />
        <Pieces state={state} seatKinds={seatKinds} texture={texture} reducedMotion={reducedMotion} outlines={settings.fullOutlines} />
        <CoinCarts rent={state.lastRent} texture={texture} reducedMotion={reducedMotion} />
        {settings.effects && view === "chart" ? (
          <Suspense fallback={null}>
            <ChartTiltShift />
          </Suspense>
        ) : null}
        {DEV_PERF ? <PerfProbe tier={tier} dpr={settings.dpr} /> : null}
      </Canvas>
      <button
        type="button"
        className={styles.viewToggle}
        onClick={() => setView((v) => (v === "street" ? "chart" : "street"))}
        aria-label={view === "street" ? "Switch to chart view (C)" : "Switch to street view (C)"}
      >
        {view === "street" ? "Chart view" : "Street view"}
        <kbd className={styles.key}>C</kbd>
      </button>
    </div>
  );
}
