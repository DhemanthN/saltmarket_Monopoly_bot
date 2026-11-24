/**
 * Screen positions of the thought-lantern anchors above agent pieces. The world writes them
 * every frame it renders; the HUD subscribes (for example with `useSyncExternalStore`) and
 * draws the lantern content there. Positions are CSS pixels inside the canvas.
 */
export interface LanternAnchor {
  seat: number;
  x: number;
  y: number;
  /** False when the anchor is behind the camera or off screen. */
  visible: boolean;
}

let anchors: readonly LanternAnchor[] = [];
const listeners = new Set<() => void>();

export function getLanternAnchors(): readonly LanternAnchor[] {
  return anchors;
}

export function subscribeLanternAnchors(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

const close = (a: LanternAnchor, b: LanternAnchor) =>
  a.seat === b.seat && a.visible === b.visible && Math.abs(a.x - b.x) < 0.5 && Math.abs(a.y - b.y) < 0.5;

/** Called by the scene. Notifies only when something moved by half a pixel or more. */
export function publishLanternAnchors(next: readonly LanternAnchor[]): void {
  if (next.length === anchors.length && next.every((a, i) => close(a, anchors[i]))) return;
  anchors = next;
  listeners.forEach((l) => l());
}
