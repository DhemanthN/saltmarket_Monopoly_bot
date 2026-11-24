import { lazy, Suspense, useState } from "react";
import type { GameSession, SessionConfig } from "./contract/types";
import { SessionHud } from "./hud/HudView";
import { StartScreen } from "./screens/StartScreen";
import { AtollSilhouette } from "./world/AtollSilhouette";

/** `/tokens`, `/world` (fixture replay) and `/hud` exist in `npm run dev` and in `npm run preview:dev` builds only. */
const DEV_PAGES = import.meta.env.DEV || import.meta.env.MODE === "devpages";

// Created only when dev pages are on, so a production build drops the chunks.
const TokensPage = DEV_PAGES ? lazy(() => import("./screens/TokensPage")) : null;
const ReplayPage = DEV_PAGES ? lazy(() => import("./world/dev/ReplayPage")) : null;
const HudPage = DEV_PAGES ? lazy(() => import("./screens/HudPage")) : null;

interface AppProps {
  /** Starts a game for the chosen table. Supplied once the runtime is connected (task 5). */
  createSession?: (config: SessionConfig) => Promise<GameSession>;
}

interface Playing {
  config: SessionConfig;
  session: GameSession;
}

export function App({ createSession }: AppProps) {
  const [playing, setPlaying] = useState<Playing | null>(null);

  const devPage = window.location.pathname;
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
    const leave = () => {
      playing.session.dispose();
      setPlaying(null);
    };
    return (
      <main style={{ position: "relative", height: "100%", overflow: "hidden" }}>
        <AtollSilhouette />
        <SessionHud session={playing.session} config={playing.config} onPlayAgain={leave} />
      </main>
    );
  }

  const onStart = createSession
    ? async (config: SessionConfig) => {
        const session = await createSession(config);
        await session.start(config);
        setPlaying({ config, session });
      }
    : undefined;
  return <StartScreen onStart={onStart} />;
}
