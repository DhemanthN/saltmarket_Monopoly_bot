import { prefersReducedMotion } from "./quality";

/** True when the person turned Calm on (the page sets `data-calm="on"` on the root element). */
export function calmOn(): boolean {
  return typeof document !== "undefined" && document.documentElement.dataset.calm === "on";
}

/** Decorative motion (ship bob, cursor trail) runs only when neither reduced motion nor Calm is set. */
export function decorativeMotionOk(): boolean {
  return !prefersReducedMotion() && !calmOn();
}

/** True on devices with a fine pointer such as a mouse; cursor, parallax and trail are desktop-only. */
export function finePointer(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(pointer: fine)").matches;
}
