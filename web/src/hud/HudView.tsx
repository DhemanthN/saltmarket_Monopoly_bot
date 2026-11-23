import { useEffect, useState } from "react";
import type { AgentName, Decision, GameEvent, GameSession, SessionConfig } from "../contract/types";
import { CoachMarks } from "./CoachMarks";
import { seatNames } from "./format";
import { DecisionPanel } from "./decisions/DecisionPanel";
import { GameOver } from "./GameOver";
import { LanternDock } from "./Lantern";
import { LedgerRail } from "./LedgerRail";
import { applyEvent, initialHudState, type HudState } from "./state";

export interface HudViewProps {
  hud: HudState;
  names: readonly string[];
  seats: readonly string[];
  decision: Decision | null;
  gameOver: boolean;
  onSubmit: (actionId: number) => void;
  onPlayAgain: () => void;
  /** Show the first-game coach marks. */
  coach?: boolean;
}

/** Everything drawn over the 3D world: ledger, lanterns, decision panel, coach marks, game over. */
export function HudView({ hud, names, seats, decision, gameOver, onSubmit, onPlayAgain, coach = false }: HudViewProps) {
  const lanterns = seats.flatMap((kind, seat) =>
    kind === "ppo" || kind === "dqn" ? [{ seat, name: names[seat], explanation: hud.explanation[seat] }] : [],
  );
  const agents = seats.filter((k): k is AgentName => k === "ppo" || k === "dqn");
  const human = seats.indexOf("human");
  return (
    <>
      <LedgerRail hud={hud} names={names} active={decision?.seat ?? null} />
      <LanternDock lanterns={lanterns} />
      {decision && !gameOver ? (
        <DecisionPanel key={`${decision.turn}-${decision.kind}-${decision.legal.map((a) => a.id).join(",")}`} decision={decision} hud={hud} names={names} onSubmit={onSubmit} />
      ) : null}
      {coach && decision && decision.seat === human ? <CoachMarks /> : null}
      {gameOver ? <GameOver hud={hud} names={names} agents={agents} onPlayAgain={onPlayAgain} /> : null}
    </>
  );
}

export interface SessionHudProps {
  session: GameSession;
  config: SessionConfig;
  onPlayAgain: () => void;
}

/** Binds `HudView` to a running `GameSession`: replays its log, then follows new events and decisions. */
export function SessionHud({ session, config, onPlayAgain }: SessionHudProps) {
  const names = seatNames(config.seats);
  const [hud, setHud] = useState<HudState>(() =>
    session.events().reduce((s, e) => applyEvent(s, e, names), initialHudState(names.length)),
  );
  const [decision, setDecision] = useState<Decision | null>(() => session.current());

  useEffect(() => {
    const offEvent = session.onEvent((e: GameEvent) => setHud((s) => applyEvent(s, e, names)));
    const offDecision = session.onDecision(setDecision);
    return () => {
      offEvent();
      offDecision();
    };
    // `names` is derived from `config`, which is fixed for the life of a session.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session]);

  const submit = (id: number) => {
    setDecision(null);
    void session.submit(id);
  };

  return (
    <HudView
      hud={hud}
      names={names}
      seats={config.seats}
      decision={decision}
      gameOver={hud.winner !== null}
      onSubmit={submit}
      onPlayAgain={onPlayAgain}
      coach
    />
  );
}
