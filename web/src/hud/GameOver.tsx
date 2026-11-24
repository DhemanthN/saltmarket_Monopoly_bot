import { useEffect, useRef, useState } from "react";
import { seatOrder } from "../styles/tokens";
import { Button } from "../ui/Button";
import { Emblem } from "../ui/Emblem";
import { LedgerRow } from "../ui/LedgerRow";
import { Panel } from "../ui/Panel";
import { useFocusTrap } from "../ui/useFocusTrap";
import { useModalKeys } from "../ui/useModalKeys";
import type { AgentName } from "../contract/types";
import { factFor, factSentence, RESULTS_URL } from "./facts";
import { money, shortName } from "./format";
import type { ResultsFact } from "./resultsFacts";
import { netWorth, type HudState } from "./state";
import styles from "./GameOver.module.css";

export interface GameOverProps {
  hud: HudState;
  names: readonly string[];
  /** Agents seated at this table. */
  agents: AgentName[];
  /** Starts a new game with the same seed and seats. */
  onReplay: () => void;
  /** Back to the start screen. */
  onMenu: () => void;
}

/** The result over the world. Escape folds it into a small bar, so the winner's atoll can be seen. */
export function GameOver({ hud, names, agents, onReplay, onMenu }: GameOverProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [folded, setFolded] = useState(false);
  useModalKeys(!folded, () => setFolded(true));
  useFocusTrap(ref, !folded);
  useEffect(() => {
    if (!folded) ref.current?.focus();
  }, [folded]);
  const winner = hud.winner ?? 0;
  if (folded) {
    return (
      <div className={styles.bar} role="region" aria-label="Game result">
        <span>
          {names[winner]} won after {hud.turns ?? hud.turn} turns
        </span>
        <Button onClick={() => setFolded(false)}>Show result</Button>
        <Button variant="primary" onClick={onReplay}>
          Replay
        </Button>
      </div>
    );
  }
  const facts = [...new Set(agents)].map((a) => factFor(a, names.length)).filter((f): f is ResultsFact => f !== null);
  return (
    <div className={styles.scrim}>
      <div ref={ref} tabIndex={-1} className={styles.focus}>
        <Panel floating className={styles.panel} aria-labelledby="over-title" role="dialog" aria-modal="true">
          <p className={styles.kicker}>Game over after {hud.turns ?? hud.turn} turns</p>
          <h2 id="over-title" className={styles.title}>
            <Emblem emblem={seatOrder[winner].emblem} seat={seatOrder[winner].name} size={32} />
            {names[winner]} wins
          </h2>
          <div className={styles.ledger}>
            {names.map((name, seat) => (
              <LedgerRow
                key={name + seat}
                mark={<Emblem emblem={seatOrder[seat].emblem} seat={seatOrder[seat].name} size={22} />}
                label={hud.bankrupt[seat] ? `${shortName(name)} (out)` : shortName(name)}
                value={money(netWorth(hud, seat))}
                active={seat === winner}
              />
            ))}
          </div>
          <p className={styles.note}>Final net worth. The same seed gives the same dice and cards.</p>
          {facts.length > 0 ? (
            <ul className={styles.facts}>
              {facts.map((f) => (
                <li key={f.agent}>{factSentence(f)}</li>
              ))}
            </ul>
          ) : agents.length > 0 ? (
            <p className={styles.note}>No measured win rate exists for this table size yet.</p>
          ) : null}
          <div className={styles.actions}>
            <Button variant="primary" onClick={onReplay}>
              Replay, same seed
            </Button>
            <Button onClick={onMenu}>Back to the start</Button>
            {agents.length > 0 ? (
              <a className={styles.link} href={RESULTS_URL} target="_blank" rel="noreferrer">
                Read the full results
              </a>
            ) : null}
          </div>
        </Panel>
      </div>
    </div>
  );
}
