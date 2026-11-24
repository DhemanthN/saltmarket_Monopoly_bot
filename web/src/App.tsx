import { lazy, Suspense } from "react";
import { StartScreen } from "./screens/StartScreen";

/** `/tokens` and `/world` (fixture replay) exist in `npm run dev` and in `npm run preview:dev` builds only. */
const DEV_PAGES = import.meta.env.DEV || import.meta.env.MODE === "devpages";

// Created only when dev pages are on, so a production build drops the chunk.
const TokensPage = DEV_PAGES ? lazy(() => import("./screens/TokensPage")) : null;
const ReplayPage = DEV_PAGES ? lazy(() => import("./world/dev/ReplayPage")) : null;

export function App() {
  if (TokensPage && window.location.pathname === "/tokens") {
    return (
      <Suspense fallback={null}>
        <TokensPage />
      </Suspense>
    );
  }
  if (ReplayPage && window.location.pathname === "/world") {
    return (
      <Suspense fallback={null}>
        <ReplayPage />
      </Suspense>
    );
  }
  return <StartScreen />;
}
