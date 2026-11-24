/** What the pointer is over in the world, shared by the 3D probe and the 2D spyglass cursor. */
export interface HoverState {
  /** Text for the floating label, or null when nothing is hovered. */
  label: string | null;
  /** Pointer position in CSS pixels, relative to the viewport. */
  x: number;
  y: number;
  /** "touch" shows the label only; "mouse" also shows the spyglass. */
  kind: "mouse" | "touch";
}

const IDLE: HoverState = { label: null, x: 0, y: 0, kind: "mouse" };
let state = IDLE;
const listeners = new Set<() => void>();

export const getHover = (): HoverState => state;

export function subscribeHover(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Publish a change. Skips the notification when the label and position are effectively unchanged. */
export function setHover(next: HoverState): void {
  const same =
    next.label === state.label && next.kind === state.kind && Math.abs(next.x - state.x) < 0.5 && Math.abs(next.y - state.y) < 0.5;
  if (same) return;
  state = next;
  listeners.forEach((l) => l());
}

export const clearHover = (): void => setHover(IDLE);
