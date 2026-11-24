import { CatmullRomCurve3, Vector3 } from "three";
import type { Tier } from "./quality";

/*
 * Pure logic for the living sea: when a flare may fly, where it goes, and the patrol routes.
 * The components in `LivingSea.tsx` only read from here, so this file is what the tests cover.
 */

/** Seconds between automatic flares: a fresh pick in [MIN, MAX) after each one. */
export const FLARE_MIN_S = 15;
export const FLARE_MAX_S = 20;
/** Seconds a flare takes from launch to splash. */
export const FLARE_FLIGHT_S = 2.4;

/** Small seeded generator (mulberry32), so a page's flare rhythm repeats and no global random is used. */
export function seededRandom(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function nextFlareDelay(random: () => number): number {
  return FLARE_MIN_S + random() * (FLARE_MAX_S - FLARE_MIN_S);
}

export interface FlareGate {
  tier: Tier;
  reducedMotion: boolean;
  calm: boolean;
  /** A human decision panel is open: nothing may pull the eye away from it. */
  decisionOpen: boolean;
}

/** Flares fly only on Medium and High, with motion allowed and no human decision waiting. */
export function flaresAllowed(g: FlareGate): boolean {
  return g.tier !== "low" && !g.reducedMotion && !g.calm && !g.decisionOpen;
}

/** Patrol galleons sail on High and Medium only. Low shows an empty sea. */
export function galleonCount(tier: Tier): number {
  return tier === "low" ? 0 : tier === "medium" ? 2 : 3;
}

/**
 * Point on a flare's arc at progress `t` in [0, 1]: straight in x and z, a parabola in y that
 * leaves `from`, peaks `height` above the chord at t = 0.5 and lands on `to`.
 */
export function flareArc(from: Vector3, to: Vector3, height: number, t: number, out = new Vector3()): Vector3 {
  const k = Math.min(1, Math.max(0, t));
  out.lerpVectors(from, to, k);
  out.y += 4 * height * k * (1 - k);
  return out;
}

/** Radius band the galleons patrol: outside the reef contours, inside the fog. */
export const PATROL_RADII = [21, 25, 29] as const;

/** Closed patrol loop `i`: a wobbling ellipse at its patrol radius, sailed with CatmullRom smoothing. */
export function patrolCurve(i: number, points = 10): CatmullRomCurve3 {
  const r = PATROL_RADII[i % PATROL_RADII.length];
  const pts: Vector3[] = [];
  for (let k = 0; k < points; k += 1) {
    const a = (k / points) * Math.PI * 2 + i * 2.1;
    const wobble = 1 + 0.08 * Math.sin(a * 3 + i);
    pts.push(new Vector3(Math.cos(a) * r * wobble, 0, Math.sin(a) * r * 0.88 * wobble));
  }
  return new CatmullRomCurve3(pts, true, "centripetal");
}

type Listener = () => void;
const listeners = new Set<Listener>();

/** Ask the scene to fire a flare now (a big event). Ignored while flares are not allowed. */
export function triggerFlare(): void {
  for (const l of listeners) l();
}

export function onFlareTrigger(l: Listener): () => void {
  listeners.add(l);
  return () => {
    listeners.delete(l);
  };
}
