import { lazy, Suspense } from "react";
import { StartScreen } from "./screens/StartScreen";

const TokensPage = lazy(() => import("./screens/TokensPage"));

/** `/tokens` exists in `npm run dev` and in `npm run preview:dev` builds only. */
const DEV_PAGES = import.meta.env.DEV || import.meta.env.MODE === "devpages";

export function App() {
  if (DEV_PAGES && window.location.pathname === "/tokens") {
    return (
      <Suspense fallback={null}>
        <TokensPage />
      </Suspense>
    );
  }
  return <StartScreen />;
}
