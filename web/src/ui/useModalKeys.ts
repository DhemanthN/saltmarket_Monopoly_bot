import { useEffect, useRef } from "react";

/** Keys the game binds on `window` (decision panel and camera). A layer on top swallows them. */
const GAME_KEYS = /^([1-9]|Enter|Escape|ArrowLeft|ArrowRight|ArrowUp|ArrowDown|c|C)$/;

/** True when a layer on top must keep this key from the game (decision panel and camera). */
export function isGameKey(e: Pick<KeyboardEvent, "key" | "ctrlKey" | "metaKey" | "altKey">): boolean {
  return !e.ctrlKey && !e.metaKey && !e.altKey && GAME_KEYS.test(e.key);
}

/** Open layers, oldest first. Only the newest one answers Escape. */
const layers: object[] = [];

/**
 * While a layer such as a tip card or the menu is open, keep game keys away from what lies under
 * it. The listener runs in the capture phase on `window`, so it sees each key before the decision
 * panel and camera listeners do. Escape calls `onEscape` of the newest open layer only, so closing
 * the menu over a tip leaves the tip open. Enter on a button still clicks it.
 */
export function useModalKeys(active: boolean, onEscape: () => void): void {
  const ref = useRef(onEscape);
  useEffect(() => {
    ref.current = onEscape;
  });

  useEffect(() => {
    if (!active) return;
    const layer = {};
    layers.push(layer);
    const onKeyDown = (e: KeyboardEvent) => {
      if (!isGameKey(e)) return;
      e.stopPropagation();
      if (e.key === "Escape" && layers[layers.length - 1] === layer) {
        e.preventDefault();
        ref.current();
      }
    };
    window.addEventListener("keydown", onKeyDown, { capture: true });
    return () => {
      window.removeEventListener("keydown", onKeyDown, { capture: true });
      layers.splice(layers.indexOf(layer), 1);
    };
  }, [active]);
}
