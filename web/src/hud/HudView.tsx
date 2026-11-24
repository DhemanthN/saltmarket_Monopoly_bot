import type { AgentName, Decision } from "../contract/types";
import { CoachMarks } from "./CoachMarks";
import { DecisionPanel } from "./decisions/DecisionPanel";
import { GameOver } from "./GameOver";
import { LanternDock } from "./Lantern";
import { LedgerRail } from "./LedgerRail";
import type { HudState } from "./state";

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
      <LedgerRail hud={hud} names={names} active={decision?.seat ?? null} human={human} />
      <LanternDock lanterns={lanterns} />
      {decision && !gameOver ? (
        <DecisionPanel key={`${decision.turn}-${decision.kind}-${decision.legal.map((a) => a.id).join(",")}`} decision={decision} hud={hud} names={names} onSubmit={onSubmit} />
      ) : null}
      {coach && decision && decision.seat === human ? <CoachMarks /> : null}
      {gameOver ? <GameOver hud={hud} names={names} agents={agents} onPlayAgain={onPlayAgain} /> : null}
    </>
  );
}
