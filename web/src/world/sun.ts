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
}

/**
 * Light for a turn. The day splits into four equal quarters, each blending from its keyframe
 * colour toward the next one. Night keeps an ambient floor so the board stays readable.
 */
export function sunForTurn(turn: number): SunState {
  const day = (((turn % TURNS_PER_DAY) + TURNS_PER_DAY) % TURNS_PER_DAY) / TURNS_PER_DAY;
  const q = day * 4;
  const i = Math.floor(q);
  const t = q - i;
  const keyframe = ORDER[i];
  const color = new Color(sunKeyframes[keyframe]).lerp(new Color(sunKeyframes[ORDER[(i + 1) % 4]]), t);
  const night = keyframe === "night";
  // Arc from east (dawn) over the top (noon) to west (dusk); the moon rides high and soft.
  const arc = night ? Math.PI / 2 : Math.min(Math.PI, (day / 0.75) * Math.PI);
  const elevation = night ? 0.9 : 0.25 + Math.sin(arc) * 0.75;
  const direction: [number, number, number] = [Math.cos(arc) * 14, elevation * 14, 8];
  const sky = new Color(night ? palette.night : worldColors.sky);
  return {
    keyframe,
    mood: night ? "night" : "day",
    direction,
    color,
    intensity: night ? 0.9 : 1.6 + Math.sin(arc) * 1.2,
    hemiIntensity: night ? 1.1 : 1.8,
    sky,
  };
}
