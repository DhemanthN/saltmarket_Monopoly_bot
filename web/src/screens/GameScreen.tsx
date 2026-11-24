import { Component, type ReactNode } from "react";
import { HudView } from "../hud/HudView";
import { useGameStore } from "../store/gameStore";
import { AtollSilhouette } from "../world/AtollSilhouette";
import { WorldScene } from "../world/WorldScene";
import { LOAD_CAPTION } from "./loadCaption";
import { RuntimeTrouble } from "./RuntimeTrouble";

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
  const retry = useGameStore((s) => s.retry);
  const ready = load.phase === "ready";

  return (
    <main style={screenStyle}>
      {ready ? (
        <>
          <WorldScene state={world} seatKinds={config.seats} />
          <HudView
            hud={hud}
            names={names}
            seats={config.seats}
            decision={trouble ? null : decision}
            gameOver={hud.winner !== null}
            onSubmit={submit}
            onPlayAgain={leave}
            coach
          />
        </>
      ) : (
        <>
          <AtollSilhouette progress={load.fraction} caption={LOAD_CAPTION[load.phase]} />
          <p className="visually-hidden" role="status">
            {LOAD_CAPTION[load.phase]}
          </p>
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
