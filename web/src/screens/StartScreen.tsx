import { useState } from "react";
import type { SessionConfig } from "../contract/types";
import { seatOrder } from "../styles/tokens";
import { Button } from "../ui/Button";
import { Emblem } from "../ui/Emblem";
import { Panel } from "../ui/Panel";
import { useToast } from "../ui/Toast";
import { AtollSilhouette } from "../world/AtollSilhouette";
import { buildConfig, opponentAllowed, TABLE_SIZES, type Opponent, type TableSize } from "./startConfig";
import styles from "./StartScreen.module.css";

const OPPONENT_LABEL: Record<Opponent, string> = {
  ppo: "PPO agent",
  dqn: "DQN agent (2 players only)",
  bot: "Scripted bot",
};

interface StartScreenProps {
  /** Called with the chosen table. Absent until the game engine is connected. */
  onStart?: (config: SessionConfig) => void;
}

export function StartScreen({ onStart }: StartScreenProps) {
  const toast = useToast();
  const [opponent, setOpponent] = useState<Opponent>("ppo");
  const [size, setSize] = useState<TableSize>(2);

  const pickSize = (next: TableSize) => {
    setSize(next);
    if (!opponentAllowed(opponent, next)) setOpponent("ppo");
  };

  const config = buildConfig(opponent, size, 0);
  const start = () => {
    if (!onStart) {
      toast("The game engine is not connected yet.");
      return;
    }
    onStart(buildConfig(opponent, size, Math.floor(Math.random() * 1_000_000)));
  };

  return (
    <main className={styles.screen}>
      <AtollSilhouette />
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
            onChange={(e) => setOpponent(e.target.value as Opponent)}
          >
            {(Object.keys(OPPONENT_LABEL) as Opponent[]).map((o) => (
              <option key={o} value={o} disabled={!opponentAllowed(o, size)}>
                {OPPONENT_LABEL[o]}
              </option>
            ))}
          </select>
        </div>

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
                {kind === "human" ? "" : kind === "ppo" ? "PPO agent" : kind === "dqn" ? "DQN agent" : "Scripted bot"}
              </span>
            </div>
          ))}
        </div>

        <div className={styles.actions}>
          <Button variant="primary" onClick={start}>
            Start game
          </Button>
          <Button variant="quiet" onClick={() => toast("The rules summary arrives with the game screen.")}>
            How to play
          </Button>
        </div>
      </Panel>
    </main>
  );
}
