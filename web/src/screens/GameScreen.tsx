import { Component, useEffect, useState, useSyncExternalStore, type ReactNode } from "react";
import { GameMenu } from "../hud/GameMenu";
import { HudView } from "../hud/HudView";
import { useGameStore } from "../store/gameStore";
import { Button } from "../ui/Button";
import { AtollSilhouette } from "../world/AtollSilhouette";
import { anyModalOpen, subscribeModal } from "../world/cameraBus";
import { prefersReducedMotion, useQualityChoice } from "../world/quality";
import { WorldScene } from "../world/WorldScene";
import { LOAD_CAPTION } from "./loadCaption";
import { RuntimeTrouble } from "./RuntimeTrouble";
import styles from "./GameScreen.module.css";

const screenStyle = { position: "relative", height: "100%", overflow: "hidden" } as const;

/** Shows the calm trouble panel instead of a blank page if anything under it throws while rendering. */
class TroubleBoundary extends Component<{ children: ReactNode; onLeave: () => void }, { error: string | null }> {
  state = { error: null as string | null };

  static getDerivedStateFromError(error: unknown) {
    return { error: error instanceof Error ? error.message : String(error) };
  }

  render() {
    if (this.state.error === null) return this.props.children;
    return (
      <main style={screenStyle}>
        <AtollSilhouette />
        <RuntimeTrouble
          detail={this.state.error}
          inGame
          onRetry={() => this.setState({ error: null })}
          onLeave={() => {
            this.setState({ error: null });
            this.props.onLeave();
          }}
        />
      </main>
    );
  }
}

/** Width at which the decision panel becomes a full-width bottom sheet (DecisionPanel.module.css). */
const SHEET_QUERY = "(max-width: 600px)";

/**
 * How many pixels the mobile decision sheet covers at the bottom of the screen, so the camera
 * can keep the player's piece above it. Zero on wide screens or with no decision open.
 */
function useSheetInset(open: boolean): number {
  const [inset, setInset] = useState(0);
  useEffect(() => {
    const el = open ? document.querySelector<HTMLElement>('[data-coach="decision"]') : null;
    if (!el) return;
    const measure = () =>
      setInset(window.matchMedia(SHEET_QUERY).matches ? Math.max(0, window.innerHeight - el.getBoundingClientRect().top) : 0);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    // The sheet slides in, so measure again once it has settled.
    const settle = window.setTimeout(measure, 350);
    window.addEventListener("resize", measure);
    return () => {
      observer.disconnect();
      window.clearTimeout(settle);
      window.removeEventListener("resize", measure);
    };
  }, [open]);
  return open ? inset : 0;
}

/** A game in progress: the atoll being built while the engine loads, then the world and the HUD. */
function Game() {
  const config = useGameStore((s) => s.config)!;
  const load = useGameStore((s) => s.load);
  const trouble = useGameStore((s) => s.trouble);
  const world = useGameStore((s) => s.world);
  const hud = useGameStore((s) => s.hud);
  const names = useGameStore((s) => s.names);
  const decision = useGameStore((s) => s.decision);
  const submit = useGameStore((s) => s.submit);
  const leave = useGameStore((s) => s.leave);
  const replay = useGameStore((s) => s.replay);
  const fastForward = useGameStore((s) => s.fastForward);
  const retry = useGameStore((s) => s.retry);
  const ready = load.phase === "ready";
  const shownDecision = trouble ? null : decision;
  const sheetInset = useSheetInset(shownDecision !== null);
  const [quality, setQuality] = useQualityChoice();
  const modalOpen = useSyncExternalStore(subscribeModal, anyModalOpen);
  const [reducedMotion, setReducedMotion] = useState(prefersReducedMotion);

  return (
    <main style={screenStyle}>
      {ready ? (
        <>
          <div inert={trouble !== null} style={{ display: "contents" }}>
            <WorldScene
              state={world}
              seatKinds={config.seats}
              bottomInset={sheetInset}
              tierOverride={quality}
              paused={trouble !== null || modalOpen}
              reducedMotion={reducedMotion}
              controls={
                <GameMenu
                  quality={quality}
                  onQuality={setQuality}
                  reducedMotion={reducedMotion}
                  onReducedMotion={setReducedMotion}
                  onLeave={leave}
                />
              }
            />
            <HudView
              hud={hud}
              names={names}
              seats={config.seats}
              decision={shownDecision}
              gameOver={hud.winner !== null}
              onSubmit={submit}
              onReplay={() => void replay()}
              onMenu={leave}
              onFastForward={fastForward}
              coach
            />
          </div>
        </>
      ) : (
        <>
          <AtollSilhouette progress={load.fraction} caption={LOAD_CAPTION[load.phase]} />
          <p className="visually-hidden" role="status">
            {LOAD_CAPTION[load.phase]}
          </p>
          {trouble ? null : (
            <Button variant="quiet" className={styles.back} onClick={leave}>
              Back to the start
            </Button>
          )}
        </>
      )}
      {trouble ? <RuntimeTrouble detail={trouble} inGame={ready} onRetry={() => void retry()} onLeave={leave} /> : null}
    </main>
  );
}

export function GameScreen() {
  const leave = useGameStore((s) => s.leave);
  return (
    <TroubleBoundary onLeave={leave}>
      <Game />
    </TroubleBoundary>
  );
}
