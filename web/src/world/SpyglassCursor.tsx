import { useSyncExternalStore } from "react";
import { getHover, subscribeHover } from "./hoverStore";
import styles from "./SpyglassCursor.module.css";

/**
 * The desktop spyglass cursor and the floating lot label. It sits above the canvas but below
 * the HUD, ignores the pointer, and grows while a lot is under it. On touch only the label
 * shows, for a moment after a tap.
 */
export function SpyglassCursor() {
  const hover = useSyncExternalStore(subscribeHover, getHover);
  const mouse = hover.kind === "mouse";
  const seen = hover.x > 0 || hover.y > 0;
  return (
    <div className={styles.layer} aria-hidden="true">
      {mouse ? (
        <svg
          className={styles.glass}
          data-over={hover.label ? "true" : undefined}
          data-active={seen ? "true" : undefined}
          style={{ transform: `translate(${hover.x}px, ${hover.y}px)` }}
          viewBox="-16 -16 32 32"
        >
          <g className={styles.scale}>
            <circle r="9" className={styles.lens} />
            <circle r="9" className={styles.rim} />
            <path d="M6.5 6.5 L15 15" className={styles.tube} />
            <path d="M-4 -4 A6 6 0 0 1 2 -6" className={styles.shine} />
          </g>
        </svg>
      ) : null}
      {hover.label ? (
        <div className={styles.label} style={{ transform: `translate(${hover.x + 18}px, ${hover.y + 18}px)` }}>
          {hover.label}
        </div>
      ) : null}
    </div>
  );
}
