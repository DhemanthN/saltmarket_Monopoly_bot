/** Quality tiers from DESIGN.md. Every tier stays under 150 draw calls and caps DPR at 2. */
export type Tier = "high" | "medium" | "low";

export interface TierSettings {
  dpr: number;
  shadowMapSize: number | null;
  /** Hull outlines on pieces and markers too (buildings always get them). */
  fullOutlines: boolean;
  /** Animated water and tilt-shift blur in chart view. */
  effects: boolean;
  /** `demand` renders only on change. */
  frameloop: "always" | "demand";
}

export function tierSettings(tier: Tier, deviceDpr: number): TierSettings {
  switch (tier) {
    case "high":
      return { dpr: Math.min(deviceDpr, 2), shadowMapSize: 2048, fullOutlines: true, effects: true, frameloop: "always" };
    case "medium":
      return { dpr: Math.min(deviceDpr, 1.5), shadowMapSize: 1024, fullOutlines: true, effects: false, frameloop: "always" };
    case "low":
      return { dpr: 1, shadowMapSize: null, fullOutlines: false, effects: false, frameloop: "demand" };
  }
}

const ORDER: readonly Tier[] = ["low", "medium", "high"];

/** One step up or down, clamped. */
export function stepTier(tier: Tier, direction: 1 | -1): Tier {
  const i = Math.min(ORDER.length - 1, Math.max(0, ORDER.indexOf(tier) + direction));
  return ORDER[i];
}

export function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches === true;
}

/** Numbers the perf-auditor reads in dev builds. */
export interface PerfSnapshot {
  tier: Tier;
  dpr: number;
  fps: number;
  drawCalls: number;
  triangles: number;
  shadowUpdates: number;
}

declare global {
  interface Window {
    __saltmarketPerf?: PerfSnapshot;
  }
}

export const DEV_PERF = import.meta.env.DEV || import.meta.env.MODE === "devpages";
