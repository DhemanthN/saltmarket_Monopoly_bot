import { Color } from "three";
import { sunKeyframes, worldColors, palette, type Mood } from "../styles/tokens";

/** One day on the atoll lasts this many turns (DESIGN.md). */
export const TURNS_PER_DAY = 24;

export type SunKeyframe = keyof typeof sunKeyframes;
const ORDER: readonly SunKeyframe[] = ["dawn", "noon", "dusk", "night"];

export interface SunState {
  keyframe: SunKeyframe;
  mood: Mood;
  /** Sun direction (unit-ish), from the scene origin toward the light. */
  direction: [number, number, number];
  color: Color;
  intensity: number;
  hemiIntensity: number;
  sky: Color;
  /** Colour at the horizon, paler than the sky overhead. */
  haze: Color;
}

/** Share of the night quarter spent in full dark before the sky begins to pale. */
const NIGHT_HOLD = 0.6;

/** The dusk-to-dawn blend: 0 in full day, 1 in full night, ramping through dusk and dawn. */
function darkness(keyframe: SunKeyframe, t: number): number {
  switch (keyframe) {
    case "dawn":
    case "noon":
      return 0;
    case "dusk":
      return t;
    case "night":
      // Full dark for most of the quarter, then the sky pales so the next day starts in light.
      return t < NIGHT_HOLD ? 1 : 1 - (t - NIGHT_HOLD) / (1 - NIGHT_HOLD);
  }
}

/** Night sky overhead and the paler glow at its horizon (DESIGN.md: night sky is the ink-teal `night` token). */
const NIGHT_HAZE = "#2F4659";

/**
 * Light for a turn. The day splits into four equal quarters, each blending from its keyframe
 * colour toward the next one. The sky, haze and lights ease from day to night through dusk and
 * back through dawn, so the night never arrives as a cut. Night keeps an ambient floor so the
 * board stays readable. The mood flips to night once the dark passes the halfway mark.
 */
export function sunForTurn(turn: number): SunState {
  const day = (((turn % TURNS_PER_DAY) + TURNS_PER_DAY) % TURNS_PER_DAY) / TURNS_PER_DAY;
  const q = day * 4;
  const i = Math.floor(q);
  const t = q - i;
  const keyframe = ORDER[i];
  const color = new Color(sunKeyframes[keyframe]).lerp(new Color(sunKeyframes[ORDER[(i + 1) % 4]]), t);
  const dark = darkness(keyframe, t);
  const night = keyframe === "night";
  // Arc from east (dawn) over the top (noon) to west (dusk); the moon rides high and soft.
  const arc = night ? Math.PI / 2 : Math.min(Math.PI, (day / 0.75) * Math.PI);
  const elevation = night ? 0.9 : 0.25 + Math.sin(arc) * 0.75;
  const direction: [number, number, number] = [Math.cos(arc) * 14, elevation * 14, 8];
  const mix = (day: number, dim: number) => day + (dim - day) * dark;
  return {
    keyframe,
    mood: dark > 0.5 ? "night" : "day",
    direction,
    color,
    intensity: mix(1.6 + Math.sin(arc) * 1.2, 1.5),
    hemiIntensity: mix(1.8, 1.4),
    sky: new Color(worldColors.sky).lerp(new Color(palette.night), dark),
    haze: new Color(worldColors.sand).lerp(new Color(NIGHT_HAZE), dark),
  };
}
