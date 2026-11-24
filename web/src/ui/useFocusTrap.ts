import { useEffect, type RefObject } from "react";

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** The elements inside `root` that Tab can reach, in document order. */
export function tabbable(root: HTMLElement): HTMLElement[] {
  return [...root.querySelectorAll<HTMLElement>(FOCUSABLE)].filter((el) => el.getClientRects().length > 0);
}

/**
 * Where Tab should send focus to stay inside a group of `count` controls, or null to let the
 * browser move normally. `index` is the focused control's position, or -1 when focus is outside.
 */
export function wrapTarget(count: number, index: number, shift: boolean): number | null {
  if (count === 0) return null;
  if (shift) return index <= 0 ? count - 1 : null;
  return index === -1 || index === count - 1 ? 0 : null;
}

/** Keeps Tab and Shift+Tab inside `ref` while `active`; focus that has strayed outside comes back. */
export function useFocusTrap(ref: RefObject<HTMLElement | null>, active = true): void {
  useEffect(() => {
    if (!active) return;
    const onKeyDown = (e: KeyboardEvent) => {
      const root = ref.current;
      if (e.key !== "Tab" || !root) return;
      const items = tabbable(root);
      if (items.length === 0) {
        e.preventDefault();
        root.focus();
        return;
      }
      const target = wrapTarget(items.length, items.indexOf(document.activeElement as HTMLElement), e.shiftKey);
      if (target !== null) {
        e.preventDefault();
        items[target].focus();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [ref, active]);
}
