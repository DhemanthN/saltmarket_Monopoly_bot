import { useEffect, useRef } from "react";
import { seatOrder } from "../styles/tokens";
import { Button } from "../ui/Button";
import { Emblem } from "../ui/Emblem";
import { LedgerRow } from "../ui/LedgerRow";
import { Panel } from "../ui/Panel";
import type { AgentName } from "../contract/types";
import { factFor, factSentence, RESULTS_URL } from "./facts";
import { money } from "./format";
import type { ResultsFact } from "./resultsFacts";
import { netWorth, type HudState } from "./state";
import styles from "./GameOver.module.css";

export interface GameOverProps {
  hud: HudState;
  names: readonly string[];
  /** Agents seated at this table. */
  agents: AgentName[];
  onPlayAgain: () => void;
}

export function GameOver({ hud, names, agents, onPlayAgain }: GameOverProps) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.focus();
  }, []);
  const winner = hud.winner ?? 0;
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
                label={hud.bankrupt[seat] ? `${name} (bankrupt)` : name}
                value={money(netWorth(hud, seat))}
                active={seat === winner}
              />
            ))}
          </div>
          <p className={styles.note}>Final net worth, from the game just played.</p>
          {facts.length > 0 ? (
            <ul className={styles.facts}>
              {facts.map((f) => (
                <li key={f.agent}>{factSentence(f)}</li>
              ))}
            </ul>
          ) : (
            <p className={styles.note}>No measured win rate exists for this table size yet.</p>
          )}
          <div className={styles.actions}>
            <Button variant="primary" onClick={onPlayAgain}>
              Play again
            </Button>
            <a className={styles.link} href={RESULTS_URL} target="_blank" rel="noreferrer">
              Read RESULTS.md
            </a>
          </div>
        </Panel>
      </div>
    </div>
  );
}
