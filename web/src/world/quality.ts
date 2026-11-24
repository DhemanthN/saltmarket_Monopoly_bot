import { useCallback, useState } from "react";

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

/** Pixel ratio cap on touch phones: a 3x screen at full ratio costs 9x the pixels for no visible gain. */
export const MOBILE_DPR_CAP = 1.5;

export function tierSettings(tier: Tier, deviceDpr: number, mobile = false): TierSettings {
  const cap = (limit: number) => Math.min(deviceDpr, mobile ? Math.min(limit, MOBILE_DPR_CAP) : limit);
  switch (tier) {
    case "high":
      return { dpr: cap(2), shadowMapSize: 2048, fullOutlines: true, effects: true, frameloop: "always" };
    case "medium":
      return { dpr: cap(1.5), shadowMapSize: 1024, fullOutlines: true, effects: false, frameloop: "always" };
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

/** A phone or tablet: the primary pointer is a finger. */
export function isMobile(): boolean {
  return typeof window !== "undefined" && window.matchMedia?.("(pointer: coarse)").matches === true;
}

/** Where auto quality starts: desktop GPUs begin on High, phones on Medium. The monitor adjusts from there. */
export function startingTier(mobile: boolean): Tier {
  return mobile ? "medium" : "high";
}

/** The tier the player picked in the menu (null means auto), remembered across reloads. */
const QUALITY_KEY = "saltmarket.quality";

export function loadQuality(): Tier | null {
  try {
    const value = window.localStorage.getItem(QUALITY_KEY);
    return value === "high" || value === "medium" || value === "low" ? value : null;
  } catch {
    return null;
  }
}

export function saveQuality(choice: Tier | null): void {
  try {
    if (choice) window.localStorage.setItem(QUALITY_KEY, choice);
    else window.localStorage.removeItem(QUALITY_KEY);
  } catch {
    // Private windows may refuse storage; the choice then lasts for this visit only.
  }
}

/** State hook for the menu's quality choice: starts from the saved pick and saves each change. */
export function useQualityChoice(): [Tier | null, (choice: Tier | null) => void] {
  const [choice, setChoice] = useState<Tier | null>(loadQuality);
  const update = useCallback((next: Tier | null) => {
    setChoice(next);
    saveQuality(next);
  }, []);
  return [choice, update];
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
  textures: number;
  geometries: number;
  shadowUpdates: number;
}

declare global {
  interface Window {
    __saltmarketPerf?: PerfSnapshot;
  }
}

/** The probe is on in dev builds, and in any build opened with `?perf=1`. */
export const DEV_PERF =
  import.meta.env.DEV ||
  import.meta.env.MODE === "devpages" ||
  (typeof window !== "undefined" && new URLSearchParams(window.location.search).get("perf") === "1");

/** Frames per second below which a window counts as slow, and at or above which it counts as healthy. */
const SLOW_FPS = 38;
const HEALTHY_FPS = 54;
/** Windows in a row needed to step down (3) or up (5); stepping up needs the longer proof. */
const WINDOWS_DOWN = 3;
const WINDOWS_UP = 5;
/** After a step down, the tier left is not retried for this long, so a borderline machine does not flip-flop. */
const RETRY_AFTER_MS = 60_000;

/**
 * Picks the quality tier from one-second frame-rate windows. Pure, so tests can feed it numbers.
 * Replaces the drei monitor, which counts sparse demand-mode frames as a slow machine.
 */
export class TierGovernor {
  tier: Tier;
  private slow = 0;
  private healthy = 0;
  private failed: { tier: Tier; at: number } | null = null;

  constructor(start: Tier) {
    this.tier = start;
  }

  /** Feed the average fps of one window. Returns the new tier when it changes, else null. */
  sample(fps: number, now: number): Tier | null {
    if (fps < SLOW_FPS) {
      this.slow += 1;
      this.healthy = 0;
    } else if (fps >= HEALTHY_FPS) {
      this.healthy += 1;
      this.slow = 0;
    } else {
      this.slow = 0;
      this.healthy = 0;
    }
    if (this.slow >= WINDOWS_DOWN && this.tier !== "low") {
      this.failed = { tier: this.tier, at: now };
      return this.move(-1);
    }
    if (this.healthy >= WINDOWS_UP && this.tier !== "high") {
      const up = stepTier(this.tier, 1);
      const blocked = this.failed?.tier === up && now - this.failed.at < RETRY_AFTER_MS;
      if (!blocked) return this.move(1);
      this.healthy = 0;
    }
    return null;
  }

  /** Follow a tier change made elsewhere, such as the player picking a tier in the menu. */
  reset(tier: Tier): void {
    this.tier = tier;
    this.slow = 0;
    this.healthy = 0;
  }

  private move(direction: 1 | -1): Tier {
    this.tier = stepTier(this.tier, direction);
    this.slow = 0;
    this.healthy = 0;
    return this.tier;
  }
}
