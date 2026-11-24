/** Geometry for the compass bar, kept pure so the heading maths can be tested. */

export const POINTS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"] as const;

/** Pixels the bar spends on one degree of heading. */
export const PIXELS_PER_DEGREE = 3.75;
const STEP = 5;

export interface Mark {
  /** Position across the bar, in pixels. */
  x: number;
  /** Tick length as a share of the bar height. */
  length: number;
  /** Heading in degrees, 0 to 359. */
  degrees: number;
  /** A compass point (every 45 degrees) is drawn brighter and named. */
  point: (typeof POINTS)[number] | null;
  /** Whether this tick carries a number (every 15 degrees that is not a point). */
  numbered: boolean;
}

const wrap = (deg: number) => ((deg % 360) + 360) % 360;

/** Nearest of the eight compass points. */
export function pointFor(heading: number): (typeof POINTS)[number] {
  return POINTS[Math.round(wrap(heading) / 45) % 8];
}

/** Reading shown beside the bar, like `045° NE`. */
export function headingText(heading: number): string {
  return `${String(Math.round(wrap(heading)) % 360).padStart(3, "0")}° ${pointFor(heading)}`;
}

/** Ticks visible in a bar `width` pixels wide when the camera faces `heading`. The centre is the heading. */
export function compassMarks(heading: number, width: number): Mark[] {
  const half = width / 2 / PIXELS_PER_DEGREE;
  const marks: Mark[] = [];
  for (let d = Math.floor((heading - half) / STEP) * STEP; d <= heading + half; d += STEP) {
    const degrees = wrap(d);
    const isPoint = degrees % 45 === 0;
    marks.push({
      x: width / 2 + (d - heading) * PIXELS_PER_DEGREE,
      length: isPoint ? 0.32 : degrees % 15 === 0 ? 0.24 : 0.13,
      degrees,
      point: isPoint ? POINTS[degrees / 45] : null,
      numbered: !isPoint && degrees % 15 === 0,
    });
  }
  return marks;
}
