import { useEffect, useId, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { modalOpened } from "../world/cameraBus";
import { Panel } from "./Panel";
import { useFocusTrap } from "./useFocusTrap";
import { useModalKeys } from "./useModalKeys";
import styles from "./Dialog.module.css";

interface DialogProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
  /** Wider dialogs hold reading text (How to play); the default suits a short menu. */
  wide?: boolean;
}

/**
 * A modal panel over a scrim, on the menu layer. Escape or a click on the scrim closes it, game
 * keys do not reach what is underneath, and focus returns to the opener on close. It renders into
 * `document.body`, so an opener inside another stacking context (the 3D world) cannot trap it.
 */
export function Dialog({ title, onClose, children, wide = false }: DialogProps) {
  const titleId = useId();
  const ref = useRef<HTMLDivElement>(null);
  useModalKeys(true, onClose);
  useFocusTrap(ref);

  // The world stops rendering behind a modal and starts again when the last one closes.
  useEffect(() => modalOpened(), []);

  useEffect(() => {
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    ref.current?.focus();
    return () => opener?.focus();
  }, []);

  return createPortal(
    <div className={styles.scrim} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div ref={ref} tabIndex={-1} className={`${styles.focus} ${wide ? styles.wide : ""}`}>
        <Panel floating className={styles.panel} role="dialog" aria-modal="true" aria-labelledby={titleId}>
          <h2 id={titleId} className={styles.title}>
            {title}
          </h2>
          {children}
        </Panel>
      </div>
    </div>,
    document.body,
  );
}
