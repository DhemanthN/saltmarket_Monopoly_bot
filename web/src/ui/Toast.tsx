import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";
import styles from "./Toast.module.css";

interface ToastItem {
  id: number;
  message: string;
}

const ToastContext = createContext<(message: string) => void>(() => undefined);

const TOAST_MS = 4000;

/** Wrap the app once. Toasts stack bottom-right (top on phones) in a polite live region. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(0);

  const show = useCallback((message: string) => {
    const id = nextId.current++;
    setItems((prev) => [...prev.slice(-2), { id, message }]);
    window.setTimeout(() => setItems((prev) => prev.filter((t) => t.id !== id)), TOAST_MS);
  }, []);

  return (
    <ToastContext.Provider value={show}>
      {children}
      <div className={styles.region} role="status" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className={styles.toast}>
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useToast(): (message: string) => void {
  return useContext(ToastContext);
}
