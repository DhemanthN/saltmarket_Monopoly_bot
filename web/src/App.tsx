import { lazy, Suspense, useEffect } from "react";
import { LOAD_CAPTION } from "./screens/loadCaption";
import { StartScreen } from "./screens/StartScreen";
import { useGameStore } from "./store/gameStore";

/** `/tokens`, `/world` (fixture replay) and `/hud` exist in `npm run dev` and in `npm run preview:dev` builds only. */
const DEV_PAGES = import.meta.env.DEV || import.meta.env.MODE === "devpages";

// Created only when dev pages are on, so a production build drops the chunks.
const TokensPage = DEV_PAGES ? lazy(() => import("./screens/TokensPage")) : null;
const ReplayPage = DEV_PAGES ? lazy(() => import("./world/dev/ReplayPage")) : null;
// The game screen pulls in Three.js, so it loads only after Start. The start screen stays light.
const GameScreen = lazy(() => import("./screens/GameScreen").then((m) => ({ default: m.GameScreen })));
const HudPage = DEV_PAGES ? lazy(() => import("./screens/HudPage")) : null;

export function App() {
  const playing = useGameStore((s) => s.config !== null);
  const load = useGameStore((s) => s.load);
  const boot = useGameStore((s) => s.boot);
  const startGame = useGameStore((s) => s.startGame);
  const gameOver = useGameStore((s) => s.hud.winner !== null);
  const devPage = window.location.pathname;
  const devPageShown = Boolean(DEV_PAGES) && ["/tokens", "/world", "/hud"].includes(devPage);

  // The engine starts loading as soon as the start screen shows, so it is usually ready by Start.
  useEffect(() => {
    if (!devPageShown) boot();
  }, [boot, devPageShown]);

  // A game lives only in this tab, so a reload or Back would lose it. Ask first, until it ends.
  useEffect(() => {
    if (!playing || gameOver) return;
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [playing, gameOver]);

  if (TokensPage && devPage === "/tokens") {
    return (
      <Suspense fallback={null}>
        <TokensPage />
      </Suspense>
    );
  }
  if (ReplayPage && devPage === "/world") {
    return (
      <Suspense fallback={null}>
        <ReplayPage />
      </Suspense>
    );
  }
  if (HudPage && devPage === "/hud") {
    return (
      <Suspense fallback={null}>
        <HudPage />
      </Suspense>
    );
  }

  if (playing) {
    return (
      <Suspense fallback={null}>
        <GameScreen />
      </Suspense>
    );
  }
  return (
    <StartScreen
      onStart={(config) => void startGame(config)}
      progress={load.fraction}
      caption={LOAD_CAPTION[load.phase]}
    />
  );
}
