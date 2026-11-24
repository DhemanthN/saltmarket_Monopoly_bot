/** Largest number of embers alive at once; also the size of the point buffers. */
export const MAX_EMBERS = 30;
/** Seconds an ember lives while it fades and drifts up. */
export const EMBER_LIFE = 0.6;
/** World units an ember drifts up over its life. */
export const EMBER_RISE = 0.5;

/**
 * Fixed-size pool for the cursor trail. Nothing is allocated after construction: a spawn
 * reuses the oldest slot, and `fade` is 1 for a fresh ember and 0 for a dead one.
 */
export class EmberPool {
  readonly positions = new Float32Array(MAX_EMBERS * 3);
  /** Per-ember colour: the ember tint scaled by its fade, so additive blending fades it out. */
  readonly colors = new Float32Array(MAX_EMBERS * 3);
  /** Age in seconds; a value at or above `EMBER_LIFE` means the slot is free. */
  readonly ages = new Float32Array(MAX_EMBERS).fill(EMBER_LIFE);
  private readonly base = new Float32Array(MAX_EMBERS);
  private next = 0;

  /** Put an ember at a world position, replacing the slot that has been in use longest. */
  spawn(x: number, y: number, z: number): void {
    const i = this.next;
    this.next = (this.next + 1) % MAX_EMBERS;
    this.ages[i] = 0;
    this.base[i] = y;
    this.positions.set([x, y, z], i * 3);
  }

  /** Age every live ember and lift it. Returns how many are still alive. */
  step(dt: number): number {
    let alive = 0;
    for (let i = 0; i < MAX_EMBERS; i += 1) {
      if (this.ages[i] >= EMBER_LIFE) continue;
      this.ages[i] = Math.min(EMBER_LIFE, this.ages[i] + dt);
      this.positions[i * 3 + 1] = this.base[i] + (this.ages[i] / EMBER_LIFE) * EMBER_RISE;
      if (this.ages[i] < EMBER_LIFE) alive += 1;
    }
    return alive;
  }

  /** Brightness of slot `i` from 1 (new) to 0 (dead or free). */
  fade(i: number): number {
    return Math.max(0, 1 - this.ages[i] / EMBER_LIFE);
  }

  /** Fill `colors` with `rgb` scaled by each ember's fade. */
  tint(rgb: readonly [number, number, number]): void {
    for (let i = 0; i < MAX_EMBERS; i += 1) {
      const f = this.fade(i);
      this.colors[i * 3] = rgb[0] * f;
      this.colors[i * 3 + 1] = rgb[1] * f;
      this.colors[i * 3 + 2] = rgb[2] * f;
    }
  }
}
