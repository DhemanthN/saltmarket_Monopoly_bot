import { useEffect } from "react";

/** Frees GPU buffers for geometries a component built itself; React Three Fiber only disposes what it created. */
export function useDispose(...items: ({ dispose(): void } | null | undefined)[]): void {
  useEffect(
    () => () => {
      for (const item of items) item?.dispose();
    },
    // The items are memoised by the caller, so they change only when the component rebuilds them.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    items,
  );
}
