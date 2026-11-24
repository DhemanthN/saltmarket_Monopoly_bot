import { useState } from "react";
import type { AgentName, Decision } from "../contract/types";
import { Button } from "../ui/Button";
import { CoachMarks } from "./CoachMarks";
import { DecisionPanel } from "./decisions/DecisionPanel";
import { GameOver } from "./GameOver";
import { LanternDock } from "./Lantern";
import { LedgerRail } from "./LedgerRail";
import type { HudState } from "./state";
import styles from "./HudView.module.css";

export interface HudViewProps {
  hud: HudState;
  names: readonly string[];
  seats: readonly string[];
  decision: Decision | null;
  gameOver: boolean;
  onSubmit: (actionId: number) => void;
  onReplay: () => void;
  onMenu: () => void;
  /** Skips the pauses between bot moves. Offered once the person is out of the game. */
  onFastForward?: () => void;
  /** Show the first-game coach marks. */
  coach?: boolean;
}

/** Everything drawn over the 3D world: ledger, lanterns, decision panel, coach marks, game over. */
export function HudView({ hud, names, seats, decision, gameOver, onSubmit, onReplay, onMenu, onFastForward, coach = false }: HudViewProps) {
  const lanterns = seats.flatMap((kind, seat) =>
    kind === "ppo" || kind === "dqn" ? [{ seat, name: names[seat], explanation: hud.explanation[seat] }] : [],
  );
  const agents = seats.filter((k): k is AgentName => k === "ppo" || k === "dqn");
  const human = seats.indexOf("human");
  const out = human >= 0 && hud.bankrupt[human] && !gameOver;
  const [coachStep, setCoachStep] = useState(0);
  return (
    <>
      <LedgerRail hud={hud} names={names} active={decision?.seat ?? null} human={human} />
      <LanternDock lanterns={lanterns} />
      {decision && !gameOver ? (
        <DecisionPanel key={`${decision.turn}-${decision.kind}-${decision.legal.map((a) => a.id).join(",")}`} decision={decision} hud={hud} names={names} onSubmit={onSubmit} />
      ) : null}
      {out ? (
        <div className={styles.out} role="status">
          <span>You are out of the game. The others play on.</span>
          {onFastForward ? <Button onClick={onFastForward}>Fast-forward to the result</Button> : null}
        </div>
      ) : null}
      {coach && decision && decision.seat === human ? <CoachMarks step={coachStep} onStep={setCoachStep} /> : null}
      {gameOver ? <GameOver hud={hud} names={names} agents={agents} onReplay={onReplay} onMenu={onMenu} /> : null}
    </>
  );
}
