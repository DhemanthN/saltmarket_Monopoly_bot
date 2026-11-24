import { useState } from "react";
import { Dialog } from "../ui/Dialog";
import type { SessionConfig } from "../contract/types";
import { seatOrder } from "../styles/tokens";
import { Button } from "../ui/Button";
import { Emblem } from "../ui/Emblem";
import { Panel } from "../ui/Panel";
import { AtollSilhouette } from "../world/AtollSilhouette";
import { HOW_TO_PLAY } from "./rules";
import { buildConfig, OPPONENT_LABEL, opponentAllowed, TABLE_SIZES, type Opponent, type TableSize } from "./startConfig";
import styles from "./StartScreen.module.css";

const SEAT_KIND: Record<Opponent, string> = {
  ppo: "PPO agent",
  dqn: "DQN agent",
  expert: "Expert bot",
  balanced: "Balanced bot",
  always_buy: "Always-buy bot",
};

interface StartScreenProps {
  /** Called with the chosen table. */
  onStart: (config: SessionConfig) => void;
  /** Engine load progress, drawn as the atoll rising behind the panel. */
  progress?: number;
  caption?: string;
}

export function StartScreen({ onStart, progress, caption }: StartScreenProps) {
  const [rulesOpen, setRulesOpen] = useState(false);
  const [opponent, setOpponent] = useState<Opponent>("ppo");
  const [size, setSize] = useState<TableSize>(2);

  const [notice, setNotice] = useState<string | null>(null);

  const pickSize = (next: TableSize) => {
    setSize(next);
    if (!opponentAllowed(opponent, next)) {
      setOpponent("ppo");
      setNotice("The DQN agent plays 2-player tables only, so the opponent is now the PPO agent.");
    } else {
      setNotice(null);
    }
  };

  const config = buildConfig(opponent, size, 0);
  const start = () => {
    onStart(buildConfig(opponent, size, Math.floor(Math.random() * 1_000_000)));
  };

  return (
    <main className={styles.screen}>
      <AtollSilhouette progress={progress} caption={caption} />
      <Panel floating className={styles.panel} aria-labelledby="start-title">
        <h1 id="start-title" className={styles.title}>
          Saltmarket
        </h1>
        <p className={styles.intro}>
          Buy lots around the atoll, build depots and outlast the other traders. Take a seat against
          trained agents.
        </p>

        <div className={styles.field}>
          <label htmlFor="opponent" className={styles.legend}>
            Opponent
          </label>
          <select
            id="opponent"
            className={styles.select}
            value={opponent}
            onChange={(e) => {
              setOpponent(e.target.value as Opponent);
              setNotice(null);
            }}
          >
            {(Object.keys(OPPONENT_LABEL) as Opponent[]).map((o) => (
              <option key={o} value={o} disabled={!opponentAllowed(o, size)}>
                {OPPONENT_LABEL[o]}
              </option>
            ))}
          </select>
        </div>

        {notice ? (
          <p className={styles.notice} role="status">
            {notice}
          </p>
        ) : null}

        <fieldset className={styles.field}>
          <legend className={styles.legend}>Table size</legend>
          <div className={styles.sizes}>
            {TABLE_SIZES.map((n) => (
              <label key={n} className={styles.size}>
                <input
                  type="radio"
                  name="table-size"
                  value={n}
                  checked={size === n}
                  onChange={() => pickSize(n)}
                />
                <span>{n} players</span>
              </label>
            ))}
          </div>
        </fieldset>

        <div className={styles.table} role="group" aria-label="Seats at the table">
          {config.seats.map((kind, i) => (
            <div className={styles.seat} key={seatOrder[i].name}>
              <Emblem emblem={seatOrder[i].emblem} seat={seatOrder[i].name} />
              <span className={styles.seatName}>
                {kind === "human" ? "You" : `${seatOrder[i].label} seat`}
              </span>
              <span className={styles.seatKind}>
                {kind === "human" ? "" : (SEAT_KIND[kind as Opponent] ?? kind.replace(/_/g, " "))}
              </span>
            </div>
          ))}
        </div>

        <div className={styles.actions}>
          <Button variant="primary" onClick={start}>
            Start game
          </Button>
          <Button variant="quiet" aria-haspopup="dialog" onClick={() => setRulesOpen(true)}>
            How to play
          </Button>
        </div>
      </Panel>
      {rulesOpen ? (
        <Dialog title="How to play" wide onClose={() => setRulesOpen(false)}>
          {HOW_TO_PLAY.map((topic) => (
            <section key={topic.title} className={styles.rule}>
              <h3 className={styles.ruleTitle}>{topic.title}</h3>
              <p className={styles.ruleBody}>{topic.body}</p>
            </section>
          ))}
          <Button variant="primary" onClick={() => setRulesOpen(false)}>
            Back
          </Button>
        </Dialog>
      ) : null}
    </main>
  );
}
