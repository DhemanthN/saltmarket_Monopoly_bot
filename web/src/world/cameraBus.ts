/**
 * Small module-level channel between the HUD and the camera: the real heading for the compass,
 * the Calm setting, the shake trigger for the cannon event, and the intro skip. Kept outside
 * React so the camera loop never waits on a render.
 */
import { prefersReducedMotion } from "./quality";

type Listener = () => void;

function emitter() {
  const listeners = new Set<Listener>();
  return {
    subscribe(fn: Listener) {
      listeners.add(fn);
      return () => void listeners.delete(fn);
    },
    emit() {
      listeners.forEach((fn) => fn());
    },
  };
}

/* ---------------------------------------------------------------- heading */

const headingBus = emitter();
let heading = 0;

/** Compass heading in whole degrees, 0 at world north (-Z), clockwise seen from above. */
export function getHeading(): number {
  return heading;
}

export const subscribeHeading = headingBus.subscribe;

/** Camera heading from a view direction. Only whole-degree changes notify the compass. */
export function headingFromDirection(x: number, z: number): number {
  const deg = (Math.atan2(x, -z) * 180) / Math.PI;
  return ((Math.round(deg) % 360) + 360) % 360;
}

export function setHeading(next: number): void {
  if (next === heading) return;
  heading = next;
  headingBus.emit();
}

/* ------------------------------------------------------------------ calm */

const CALM_KEY = "saltmarket.calm";
const calmBus = emitter();

function readCalm(): boolean {
  try {
    return window.localStorage.getItem(CALM_KEY) === "1";
  } catch {
    return false;
  }
}

let calmChoice = typeof window !== "undefined" && readCalm();

/** The person's Calm choice from the menu. */
export function getCalmChoice(): boolean {
  return calmChoice;
}

export function setCalmChoice(on: boolean): void {
  calmChoice = on;
  try {
    window.localStorage.setItem(CALM_KEY, on ? "1" : "0");
  } catch {
    /* Storage can be blocked; the choice then lasts for this visit only. */
  }
  calmBus.emit();
}

export const subscribeCalm = calmBus.subscribe;

/** Calm is on when the person chose it or the system asks for reduced motion. */
export function isCalm(): boolean {
  return calmChoice || prefersReducedMotion();
}

/* ----------------------------------------------------------------- shake */

export interface Shake {
  intensity: number;
  duration: number;
  startedAt: number;
}

let shake: Shake | null = null;

/** Longest shake: keeps a stray call from rattling the view. */
const MAX_SHAKE_S = 1.5;

/**
 * Rattles the camera and punches the field of view, for the cannon event. `intensity` runs 0 to 1,
 * `duration` is in seconds. Does nothing in Calm.
 */
export function triggerCameraShake(intensity: number, duration: number, now: number = performance.now()): void {
  if (isCalm() || intensity <= 0 || duration <= 0) return;
  shake = { intensity: Math.min(1, intensity), duration: Math.min(MAX_SHAKE_S, duration), startedAt: now };
}

/** The shake in progress, or null once it has played out. */
export function activeShake(now: number): Shake | null {
  if (shake && now - shake.startedAt >= shake.duration * 1000) shake = null;
  return shake;
}

/** Strength 1 to 0 across a shake, easing out so it settles instead of stopping. */
export function shakeDecay(s: Shake, now: number): number {
  const t = Math.min(1, (now - s.startedAt) / (s.duration * 1000));
  return (1 - t) * (1 - t);
}

/* -------------------------------------------------------------- decision */

let decisionOpen = false;

/** The HUD tells the camera a decision panel is open, so parallax holds still behind it. */
export function setDecisionOpen(open: boolean): void {
  decisionOpen = open;
}

export function isDecisionOpen(): boolean {
  return decisionOpen;
}

/* ----------------------------------------------------------------- modal */

const modalBus = emitter();
let modals = 0;

/** Counts full-screen dialogs so the world can stop rendering behind them. */
export function modalOpened(): () => void {
  modals += 1;
  modalBus.emit();
  let closed = false;
  return () => {
    if (closed) return;
    closed = true;
    modals -= 1;
    modalBus.emit();
  };
}

export function anyModalOpen(): boolean {
  return modals > 0;
}

export const subscribeModal = modalBus.subscribe;

/* ----------------------------------------------------------------- intro */

let introGateOpen = true;

/** The loading screen holds the intro swoop until it has faded, so the swoop is seen. */
export function armIntro(): void {
  introGateOpen = false;
}

export function releaseIntro(): void {
  introGateOpen = true;
}

export function isIntroGateOpen(): boolean {
  return introGateOpen;
}
