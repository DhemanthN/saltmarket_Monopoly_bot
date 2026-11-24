import { RING_RADIUS, ringPosition, spaces } from "./board";

/** How close to a lot's centre, in world units, the pointer counts as over it. */
const PICK_RADIUS = 0.75;

/** Index of the lot under a ground point, or null when the point is over open water or the plaza. */
export function pickSpace(x: number, z: number): number | null {
  if (Math.abs(Math.hypot(x, z) - RING_RADIUS) > PICK_RADIUS) return null;
  let best: number | null = null;
  let bestDistance = PICK_RADIUS;
  for (let i = 0; i < spaces.length; i += 1) {
    const p = ringPosition(i);
    const d = Math.hypot(p.x - x, p.z - z);
    if (d < bestDistance) {
      best = i;
      bestDistance = d;
    }
  }
  return best;
}

const words = (text: string) => text.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

/** Floating label for a lot: its name and its district, or its kind for non-property spaces. */
export function spaceLabel(index: number): string {
  const space = spaces[index];
  return `${space.name}, ${space.district ? `${words(space.district)} district` : words(space.kind)}`;
}
