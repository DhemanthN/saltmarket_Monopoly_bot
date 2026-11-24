import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { lazy, Suspense, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { type DirectionalLight } from "three";
import { Buildings } from "./Buildings";
import { CameraRig, type CameraView } from "./CameraRig";
import { CoinCarts } from "./CoinCarts";
import { Sky } from "./Sky";
import { Signboards } from "./Signboards";
import { Atoll } from "./Atoll";
import { followSeatFor } from "./follow";
import { Pieces } from "./Pieces";
import { paletteTexture } from "./palette";
import { DEV_PERF, isMobile, prefersReducedMotion, startingTier, tierSettings, TierGovernor, type Tier } from "./quality";
import type { WorldState } from "./reduceEvents";
import { sunForTurn } from "./sun";
import "./quietUpstream";
import styles from "./WorldScene.module.css";

// Loaded only when the high tier shows chart view, so other tiers never download it.
const ChartTiltShift = lazy(() => import("./ChartTiltShift"));

interface Props {
  state: WorldState;
  seatKinds: readonly string[];
  /** Tier the player picked; null lets the performance monitor decide. */
  tierOverride?: Tier | null;
  /** Cut camera moves and piece animation. Defaults to the system's reduced-motion setting. */
  reducedMotion?: boolean;
  /** HUD controls drawn in the corner beside the camera view button (the game menu). */
  controls?: ReactNode;
  /** Pixels at the bottom of the screen covered by the HUD (the mobile decision sheet). */
  bottomInset?: number;
  /** Stop rendering while a full-screen panel covers the world. A hidden tab always pauses. */
  paused?: boolean;
}

/**
 * Sun and moon. The shadow map renders only when the board changes or the sun keyframe changes,
 * at most once per turn, never per frame.
 */
function Lights({ turn, boardVersion, shadowMapSize, fog }: { turn: number; boardVersion: number; shadowMapSize: number | null; fog: number }) {
  const sun = useMemo(() => sunForTurn(turn), [turn]);
  const light = useRef<DirectionalLight>(null);
  const { gl, scene, invalidate } = useThree();
  const shadowUpdates = useRef(0);

  // Three.js renderer and scene objects are mutable by design; R3F hands them out for this.
  /* eslint-disable react-hooks/immutability */
  useEffect(() => {
    // The Canvas `shadows` prop is read once, so a tier change at runtime must toggle it here.
    gl.shadowMap.enabled = shadowMapSize !== null;
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
      <fogExp2 attach="fog" args={[sun.sky.getHex(), fog]} />
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

/** Numbers for the perf-auditor at `window.__saltmarketPerf`, in dev builds and with `?perf=1`. */
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
      textures: gl.info.memory.textures,
      geometries: gl.info.memory.geometries,
      shadowUpdates: window.__saltmarketPerf?.shadowUpdates ?? 0,
    };
    // Runs before this frame renders, so the numbers above are the previous frame's totals.
    gl.info.reset();
  });
  return null;
}

/**
 * Measures real frame rate in one-second windows and reports each to the governor. It counts
 * only frames that actually rendered, so a demand-mode scene never looks slow, and it drops any
 * window with a long stall (tab switch, shader compile) instead of blaming the tier for it.
 */
function FrameMeter({ onWindow }: { onWindow: (fps: number) => void }) {
  const window_ = useRef({ n: 0, t: 0, stalled: false });
  useFrame((_, dt) => {
    const w = window_.current;
    w.n += 1;
    w.t += dt;
    if (dt > 0.4) w.stalled = true;
    if (w.t >= 1) {
      if (!w.stalled) onWindow(w.n / w.t);
      w.n = 0;
      w.t = 0;
      w.stalled = false;
    }
  });
  return null;
}

/** Fog thickness: street view fades the far shore; chart view sits further back and needs less. */
const STREET_FOG = 0.014;
const CHART_FOG = 0.004;

/** How often a low auto tier tests the machine again, and for how long each test runs. */
const PROBE_EVERY_MS = 20_000;
const PROBE_FOR_MS = 7_000;

/** The 3D atoll. It renders a `WorldState` and never reads events. */
export function WorldScene({ state, seatKinds, tierOverride = null, controls, bottomInset = 0, paused = false, reducedMotion: motionChoice }: Props) {
  const systemReduced = useMemo(() => prefersReducedMotion(), []);
  const reducedMotion = motionChoice ?? systemReduced;
  const mobile = useMemo(() => isMobile(), []);
  const [autoTier, setAutoTier] = useState<Tier>(() => startingTier(mobile));
  const [governor] = useState(() => new TierGovernor(startingTier(mobile)));
  const tier = tierOverride ?? autoTier;
  const [hidden, setHidden] = useState(() => typeof document !== "undefined" && document.hidden);
  const [probing, setProbing] = useState(false);
  const settings = tierSettings(tier, typeof window === "undefined" ? 1 : window.devicePixelRatio, mobile);
  // Low renders on demand, which starves the frame meter. While auto sits on Low, switch to
  // continuous frames for a short probe now and then, so the scene can climb back when it can.
  const frameloop = paused || hidden ? "never" : probing ? "always" : settings.frameloop;
  const [view, setView] = useState<CameraView>("street");
  const sun = sunForTurn(state.turn);
  const texture = paletteTexture(sun.mood);
  const followSeat = followSeatFor(state, seatKinds);
  const shadows = settings.shadowMapSize !== null;

  useEffect(() => {
    const onVisibility = () => setHidden(document.hidden);
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, []);

  useEffect(() => {
    if (tierOverride !== null || autoTier !== "low") return;
    let stop: number | undefined;
    const start = window.setInterval(() => {
      setProbing(true);
      stop = window.setTimeout(() => setProbing(false), PROBE_FOR_MS);
    }, PROBE_EVERY_MS);
    return () => {
      window.clearInterval(start);
      window.clearTimeout(stop);
      setProbing(false);
    };
  }, [tierOverride, autoTier]);

  // The sky decides the page mood, so panels and chrome darken with the night.
  useEffect(() => {
    document.documentElement.dataset.mood = sun.mood;
    return () => {
      delete document.documentElement.dataset.mood;
    };
  }, [sun.mood]);

  const onWindow = (fps: number) => {
    if (tierOverride !== null) return;
    const next = governor.sample(fps, performance.now());
    if (next) setAutoTier(next);
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() !== "c" || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.target instanceof HTMLElement && e.target.closest("input, textarea, select")) return;
      setView((v) => (v === "street" ? "chart" : "street"));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className={styles.world}>
      <Canvas
        frameloop={frameloop}
        dpr={settings.dpr}
        shadows={shadows ? "percentage" : false}
        camera={{ fov: 42, near: 0.3, far: 180, position: [0, 30, 21] }}
      >
        <FrameMeter onWindow={onWindow} />
        <Lights turn={state.turn} boardVersion={state.boardVersion} shadowMapSize={settings.shadowMapSize} fog={view === "chart" ? CHART_FOG : STREET_FOG} />
        <CameraRig view={view} followSeat={followSeat} followSpace={state.position[followSeat] ?? 0} reducedMotion={reducedMotion} bottomInset={bottomInset} />
        <Sky sky={sun.sky} haze={sun.haze} texture={texture} />
        <Atoll texture={texture} shadows={shadows} seatCount={seatKinds.length} chart={view === "chart"} />
        <Signboards state={state} fromSpace={state.position[followSeat] ?? 0} street={view === "street"} seatKinds={seatKinds} />
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
      <div className={styles.corner}>
        {controls}
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
    </div>
  );
}
