import { useEffect, useRef } from "react";

export interface DecisionKeyHandlers {
  /**
   * Enter, when focus is not on a button (buttons activate natively). Choice chips
   * (`role="radio"`) only select, so Enter on one still submits the decision.
   */
  onEnter?: () => void;
  /** Escape: the secondary "do nothing" action. */
  onEscape?: () => void;
  /** Digit keys 1-9, as a zero-based index. */
  onDigit?: (index: number) => void;
  /** Left and right arrows. */
  onArrow?: (step: -1 | 1) => void;
  /** Up and down arrows. */
  onVertical?: (step: -1 | 1) => void;
}

function isTypingTarget(target: EventTarget | null): boolean {
  return target instanceof HTMLElement && ["INPUT", "SELECT", "TEXTAREA"].includes(target.tagName);
}

/** Keyboard support for one decision. Handlers are read through a ref, so they can change every render. */
export function useDecisionKeys(handlers: DecisionKeyHandlers, enabled = true): void {
  const ref = useRef(handlers);
  useEffect(() => {
    ref.current = handlers;
  });

  useEffect(() => {
    if (!enabled) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey || isTypingTarget(e.target)) return;
      const h = ref.current;
      const onButton = e.target instanceof HTMLButtonElement && e.target.getAttribute("role") !== "radio";
      if (e.key === "Enter" && h.onEnter && !onButton) {
        e.preventDefault();
        h.onEnter();
      } else if (e.key === "Escape" && h.onEscape) {
        e.preventDefault();
        h.onEscape();
      } else if (/^[1-9]$/.test(e.key) && h.onDigit) {
        e.preventDefault();
        h.onDigit(Number(e.key) - 1);
      } else if ((e.key === "ArrowLeft" || e.key === "ArrowRight") && h.onArrow) {
        e.preventDefault();
        h.onArrow(e.key === "ArrowLeft" ? -1 : 1);
      } else if ((e.key === "ArrowUp" || e.key === "ArrowDown") && h.onVertical) {
        e.preventDefault();
        h.onVertical(e.key === "ArrowUp" ? -1 : 1);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [enabled]);
}
