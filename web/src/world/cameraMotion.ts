/** Pure maths for the camera's extra motion, kept apart from the rig so tests can reach it. */

export const INTRO_SECONDS = 2.5;
/** How much farther and higher than the chart pose the intro swoop starts. */
export const INTRO_START_SCALE = 1.35;

/** Smooth start and finish: 0 to 1 over `t` in 0 to 1. */
export function easeInOutCubic(t: number): number {
  const x = Math.min(1, Math.max(0, t));
  return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
}

/** Share of the intro done after `elapsed` seconds. */
export function introProgress(elapsed: number): number {
  return easeInOutCubic(elapsed / INTRO_SECONDS);
}

/** Sway: a slow drift of a few centimetres, so a still street view never looks frozen. */
export const SWAY_AMOUNT = 0.05;

export function swayOffset(seconds: number): { x: number; y: number } {
  return { x: Math.sin(seconds * 0.45) * SWAY_AMOUNT, y: Math.sin(seconds * 0.31 + 1.3) * SWAY_AMOUNT * 0.6 };
}

/** Mouse parallax reach in world units each way. */
export const PARALLAX_AMOUNT = 0.35;

/** Pointer position in the window, as -1 to 1 on each axis. */
export function pointerUnit(clientX: number, clientY: number, width: number, height: number): { x: number; y: number } {
  const clamp = (v: number) => Math.min(1, Math.max(-1, v));
  return { x: clamp((clientX / Math.max(1, width)) * 2 - 1), y: clamp((clientY / Math.max(1, height)) * 2 - 1) };
}

/** Field-of-view punch in degrees at full strength. */
export const SHAKE_FOV_PUNCH = 3.5;
/** Position shake in world units at full strength. */
export const SHAKE_REACH = 0.18;

/** Shake displacement for a strength of 0 to 1 at `seconds`. Two unrelated sines read as noise. */
export function shakeOffset(strength: number, seconds: number): { x: number; y: number } {
  return {
    x: Math.sin(seconds * 53) * SHAKE_REACH * strength,
    y: Math.sin(seconds * 71 + 2) * SHAKE_REACH * strength,
  };
}
